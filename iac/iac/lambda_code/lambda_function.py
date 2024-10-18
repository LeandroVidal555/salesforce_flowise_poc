import json
import os
import boto3
from botocore.exceptions import ClientError
import requests
from fitz import open as fitz_open

# Initialize the DynamoDB client
dynamodb = boto3.resource('dynamodb')
# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')
# Initialize the S3 client
s3 = boto3.client('s3')

# Get environment vars
secret_creds_name = os.getenv("SECRET_CREDS_NAME")
base_url = os.getenv("BASE_URL")
file_download_path = os.getenv("FILE_DOWNLOAD_PATH")
bucket = os.getenv("BUCKET_PATH").split("/")[0]
bucket_path = "/".join(os.getenv("BUCKET_PATH").split("/")[1:])
dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME")



def sf_get_token():
    # Get SF credentials
    print("Getting SM creds...")
    response = sm.get_secret_value(SecretId=secret_creds_name)

    client_id = json.loads(response["SecretString"])["consumer-key"]
    client_secret = json.loads(response["SecretString"])["consumer-secret"]

    # Prepare request parameters
    url_auth = base_url + "/services/oauth2/token"

    payload_auth = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    print("Getting SF token...")
    res = requests.post(url_auth, headers={"Content-Type":"application/x-www-form-urlencoded"}, data=payload_auth)

    if res.status_code != 200:
        raise Exception(f"Failed to retrieve token: {res.status_code} {res.reason}")

    ### extracting token from auth call
    res_auth = json.loads(res.content)
    token = res_auth["access_token"]

    return token




def sf_get_doc_text(doc_id, token):
    url_download = base_url + f"/{file_download_path}/{doc_id}/content"

    ### Call to Salesforce API
    print("Downloading file...")
    print(url_download)
    res = requests.get(url_download, headers = {"Content-Type": "application/json", "Authorization":"Bearer " + token})

    if res.status_code != 200:
        raise Exception(f"Failed to download file: {res.status_code} {res.reason}")

    print("Saving file...")
    with open("/tmp/download.pdf", "wb") as file:
        # Use iter_content to write the file in chunks
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                file.write(chunk)

    print("Extracting text...")
    with fitz_open("/tmp/download.pdf") as pdf_file:  
        with open("/tmp/extracted.txt", 'w') as txt_file:
            for page in pdf_file:
                txt_file.write(page.get_text("text") + '\n')
    with open("/tmp/extracted.txt", 'r') as txt_file:
        extracted_text = txt_file.read()

    return extracted_text




def upload_files_s3(doc_id):
    # Upload the files
    print("Uploading original PDF file...")
    try:
        file_name = f"{bucket_path}/{doc_id}_original.pdf"
        s3.upload_file("/tmp/download.pdf", bucket, file_name)
        print(f"File {file_name} uploaded to {bucket}")
    except FileNotFoundError:
        print(f"The file {file_name} was not found")

    print("Uploading text file...")
    try:
        file_name = f"{bucket_path}/{doc_id}_extracted.txt"
        s3.upload_file("/tmp/extracted.txt", bucket, file_name)
        print(f"File {file_name} uploaded to {bucket}")
    except FileNotFoundError:
        print(f"The file {file_name} was not found")




def insert_item_dynamodb(item):
    # Put item into DynamoDB
    table = dynamodb.Table(dynamodb_table_name)
    
    print("Inserting item into DynamoDB...")
    try:
        table.put_item(Item=item)
        print('Item successfully inserted')
    except ClientError as e:
        print(f"Failed to insert item: {e.response['Error']['Message']}")




def lambda_handler(event, context):
    try:
        print("Received event: " + json.dumps(event, indent=2))
    except Exception:
        print('Event processing failed')
    else:
        print('Event processing successful')

    # Extract information from the event
    pk = event['source']
    sk = event['time']
    subject = event['detail']['payload']['Action__c']
    doc_id = event['detail']['payload']['Data__c'].split("'")[1]

    token = sf_get_token()
    extracted_text = sf_get_doc_text(doc_id, token)
    upload_files_s3(doc_id)
    
    # Prepare DynamoDB item
    item = {
        'pk': pk,
        'sk': sk,
        'subject': subject, 
        'extractedText': extracted_text
    }

    insert_item_dynamodb(item)