from lambda_function_utils_extxt import *
import json
import os
import requests
import sys
import urllib.parse
import boto3



# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")
bucket_path_fw_ds = os.getenv("BUCKET_PATH_FW_DS")
secret_fw_creds_name = os.getenv("SECRET_FW_CREDS_NAME")
fw_chatflow = os.getenv("FW_CHATFLOW")
supported_formats = json.loads(os.getenv("SUPPORTED_FORMATS"))
supported_formats_img = json.loads(os.getenv("SUPPORTED_FORMATS_IMG"))


# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')
# Initialize the S3 client
s3 = boto3.client('s3')
# Initialize the SSM client
ssm = boto3.client('ssm')



def create_text_file(text):
    print("Creating text file with the text included in the event...")
    with open("/tmp/event.txt", 'w') as f:
        f.write(text)



def upload_files_s3(rec_id, filename, doc_id=None):
    if doc_id is None:
        print("Uploading generated event text file...")
        try:
            file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename}"
            s3.upload_file("/tmp/event.txt", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")

    else:
        filename_decoded = urllib.parse.unquote(filename)
        filename_base, filename_ext = os.path.splitext(filename_decoded)
        filename_ext = filename_ext.lower()

        # Upload the file - flowise (general)
        if not filename_base.startswith("sffile_"):
            filename_base = "sffile_" + filename_base
        
        try:
            print("Uploading original file...")
            file_path_full = f"{bucket_path_fw_ds}/{rec_id}/{filename_base}_{doc_id}{filename_ext}"
            s3.upload_file("/tmp/download", bucket_name, file_path_full)
            print(f"File {file_path_full} uploaded to {bucket_name}")
        except Exception as e:
            print(f"Found error while uploading {file_path_full}: {e}")

        # Upload the file - flowise (image extracted text)
        if filename_ext in supported_formats_img:
            file_path = extract_txt_from_img(rec_id, filename_base, doc_id)

        # Upload the file - flowise (xlsx extracted csvs)
        elif filename_ext == ".xlsx":
            file_path = extract_txt_from_xlsx(rec_id, filename_base, doc_id)

        # Upload the file - flowise (docx extracted text)
        elif filename_ext == ".docx":
            file_path = extract_txt_from_docx(rec_id, filename_base, doc_id)

        # Upload the file - flowise (pdf extracted text)
        elif filename_ext == ".pdf":
            file_path = extract_txt_from_pdf(rec_id, filename_base, doc_id) # not using Flowise native doc store extractor as it is quite faulty

    return file_path, file_path_full



def fw_get_api_key():
    print("Getting FW api key from SM...")
    res = sm.get_secret_value(SecretId=secret_fw_creds_name)

    return res["SecretString"]



def upsert_vector(cf_distro_domain, chatflow, fw_api_key, file_path, file_path_source, rec_id):
    print("Upserting vector data...")
    try:
        res = requests.post(
            f"https://{cf_distro_domain}/api/v1/vector/upsert/{chatflow["id"]}",
            headers={"Authorization":f"Bearer {fw_api_key}","Content-Type":"application/json"},
            json={"overrideConfig":{"prefix":f"{file_path}","metadata":{"source": file_path_source, "record_id": rec_id}}}
        )
    except Exception as e:
        print(f"Found error while upserting: {e}")
        sys.exit(1)

    if res.status_code != 200:
        print(f"Error in upsertion procedure, got from API: {res.status_code}: {res.reason}")
        sys.exit(1)
    else:
        print("Document Store vector data upsertion succeeded.")
        #print(res.json())



def upsert_process(file_path, orig_filename, rec_id, fw_api_key):
    # First search for the target chatflow using Flowise API
    cf_distro_domain = ssm.get_parameter(Name=f"/{common_prefix}-{env}/pipeline/cf_distro_domain")['Parameter']['Value']

    try:
        res = requests.get(
            f"https://{cf_distro_domain}/api/v1/chatflows",
            headers={"Authorization":f"Bearer {fw_api_key}"}
        )
    except Exception as e:
        print(f"Found error while searching for chatflow: {e}")
        sys.exit(1)
    

    if res.status_code != 200:
        print(f"Error in chatflow search, got from API: {res.status_code}: {res.reason}")
        sys.exit(1)
    else:
        chatflow = next((d for d in res.json() if d["name"] == fw_chatflow), None)

        if chatflow != None:
            print(f"Found chatflow: {chatflow["id"]}")
        else:
            print(f"Could not find chatflow '{fw_chatflow}'")
            sys.exit(1)

    # if it's an excel file, use a slightly different approach for the prefix
    if orig_filename.endswith(".xlsx"):
        file_path = "_".join(file_path.split("_")[:-1]) # this is the prefix that matches all of the file's sheets
        file_path_source = file_path + ".xlsx"
    else:
        file_path_source = "/".join(file_path.split("/")[1:])
    
    # UPSERT VECTOR DATA
    upsert_vector(cf_distro_domain, chatflow, fw_api_key, file_path, file_path_source, rec_id)