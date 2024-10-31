import json
import os
import re
import requests
import urllib.parse
import boto3
from botocore.exceptions import ClientError


# Get environment vars
secret_sf_creds_name = os.getenv("SECRET_SF_CREDS_NAME")
base_url_sf = os.getenv("BASE_URL_SF")
file_download_path = os.getenv("FILE_DOWNLOAD_PATH")
bucket_name = os.getenv("BUCKET_NAME")
bucket_path_extxt = os.getenv("BUCKET_PATH_EXTXT")
bucket_path_fw_ds = os.getenv("BUCKET_PATH_FW_DS")
extract_text = os.getenv("EXTRACT_TEXT").lower() == "true" # booleans come as strings
dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME")
secret_fw_creds_name = os.getenv("SECRET_FW_CREDS_NAME")
fw_chatflow = os.getenv("FW_CHATFLOW")


# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')
# Initialize the S3 client
s3 = boto3.client('s3')

if extract_text:
    # Initialize the DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    # Import text extraction tool
    from fitz import open as fitz_open




def sf_get_token():
    # Get SF credentials
    print("Getting SM creds...")
    res = sm.get_secret_value(SecretId=secret_sf_creds_name)

    client_id = json.loads(res["SecretString"])["consumer-key"]
    client_secret = json.loads(res["SecretString"])["consumer-secret"]

    # Prepare request parameters
    url_auth = base_url_sf + "/services/oauth2/token"

    payload_auth = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    print("Getting SF token...")
    res = requests.post(url_auth, headers={"Content-Type":"application/x-www-form-urlencoded"}, data=payload_auth)

    if res.status_code != 200:
        raise Exception(f"Failed to retrieve token: {res.status_code} {res.reason}")
    else:
        print("token retrieval succeeded.")

    ### extracting token from auth call
    res_auth = json.loads(res.content)
    token = res_auth["access_token"]

    return token




def dl_sf_file(doc_id, token):
    url_download = base_url_sf + f"/{file_download_path}/{doc_id}/content"

    ### Call to Salesforce API
    print("Downloading file...")
    res = requests.get(url_download, headers = {"Content-Type": "application/json", "Authorization":"Bearer " + token})

    if res.status_code != 200:
        raise Exception(f"Failed to download file: {res.status_code} {res.reason}")
    
    filename = re.search(r'filename="(.+)"', res.headers["Content-Disposition"]).group(1)

    print("Saving file...")
    with open(f"/tmp/download.pdf", "wb") as file:
        # Use iter_content to write the file in chunks
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                file.write(chunk)
    
    return filename




def upload_files_s3(rec_id, doc_id, filename):
    filename_decoded = urllib.parse.unquote(filename)
    filename_base, filename_ext = os.path.splitext(filename_decoded)

    # Upload the files - text extract
    if extract_text:
        print("Uploading original PDF file...")
        try:
            file_path = f"{bucket_path_extxt}/{filename_base}_original.pdf"
            s3.upload_file("/tmp/download.pdf", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except FileNotFoundError:
            print(f"The file {file_path} was not found")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")

        print("Uploading text file...")
        try:
            file_path = f"{bucket_path_extxt}/{filename_base}_extracted.txt"
            s3.upload_file("/tmp/extracted.txt", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except FileNotFoundError:
            print(f"The file {file_path} was not found")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")

    # Upload the files - flowise document store
    print("Uploading PDF file for upsertion...")
    if filename_decoded.startswith("contacts_"):
        try:
            file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename_base}_{doc_id}{filename_ext}"
            s3.upload_file(f"/tmp/download.pdf", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except FileNotFoundError:
            print(f"The file {file_path} was not found")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")
    else:
        print("ERROR: file does not exist or does not start with 'contacts_'")




def sf_get_doc_text():
    print("Extracting text...")
    with fitz_open(f"/tmp/download.pdf") as pdf_file:  
        with open("/tmp/extracted.txt", 'w') as txt_file:
            for page in pdf_file:
                txt_file.write(page.get_text("text") + '\n')
    with open("/tmp/extracted.txt", 'r') as txt_file:
        extracted_text = txt_file.read()

    return extracted_text




def insert_item_dynamodb(item):
    # Put item into DynamoDB
    table = dynamodb.Table(dynamodb_table_name)
    
    print("Inserting item into DynamoDB...")
    try:
        table.put_item(Item=item)
        print('Item successfully inserted.')
    except ClientError as e:
        print(f"Failed to insert item: {e.response['Error']['Message']}")




def fw_get_api_key():
    # Get FW api key
    print("Getting SM creds...")
    res = sm.get_secret_value(SecretId=secret_fw_creds_name)

    return res["SecretString"]




def load_process_upsert(rec_id, fw_api_key):
    # UPSERT VECTOR DATA
    print("Upserting vector data...", end="")
    res = requests.post(
        f"https://d2br9m4wtztkg9.cloudfront.net/api/v1/vector/upsert/{fw_chatflow}",
        headers={"Authorization":f"Bearer {fw_api_key}","Content-Type":"application/json"},
        json={"overrideConfig":{"prefix":f"flowise_doc_store/{rec_id}/contacts_","metadata":{"record_id": rec_id}}}
    )

    if res.status_code != 200:
        raise Exception(f"Error in upsertion procedure, got from API: {res.status_code}: {res.reason}")
    else:
        print("Document Store vector data upsertion succeeded.")