import os
import sys
import requests
import boto3


# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")
bucket_path_fw_ds = os.getenv("BUCKET_PATH_FW_DS")
secret_fw_creds_name = os.getenv("SECRET_FW_CREDS_NAME")
fw_chatflow = os.getenv("FW_CHATFLOW")


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



def upload_files_s3(rec_id, filename):

    print("Uploading generated event text file...")
    try:
        file_path = f"{bucket_path_fw_ds}/{rec_id}/graph/{filename}"
        s3.upload_file("/tmp/event.txt", bucket_name, file_path)
        print(f"File {file_path} uploaded to {bucket_name}")
    except Exception as e:
        print(f"Found error while uploading {file_path}: {e}")
    
    return file_path



def fw_get_api_key():
    # Get FW api key
    print("Getting SM creds...")
    res = sm.get_secret_value(SecretId=secret_fw_creds_name)

    return res["SecretString"]



def load_process_upsert(file_path, orig_filename, rec_id, fw_api_key):
    # First search for the target chatflow using Flowise API
    cf_distro_domain = ssm.get_parameter(
        Name=f"/{common_prefix}-{env}/pipeline/cf_distro_domain",
    )['Parameter']['Value']

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

    file_path_source = "/".join(file_path.split("/")[1:])
    
    # UPSERT VECTOR DATA
    print("Upserting vector data...")
    try:
        res = requests.post(
            f"https://{cf_distro_domain}/api/v1/vector/upsert/{chatflow["id"]}",
            headers={"Authorization":f"Bearer {fw_api_key}","Content-Type":"application/json"},
            json={"overrideConfig":{"prefix":f"{file_path}", "tableName": "graph_text", "metadata":{"source": file_path_source, "record_id": rec_id}}}
        )
    except Exception as e:
        print(f"Found error while upserting: {e}")
        sys.exit(1)

    if res.status_code != 200:
        print(f"Error in upsertion procedure, got from API: {res.status_code}: {res.reason}")
        sys.exit(1)
    else:
        print("Document Store vector data upsertion succeeded.")
        print(res.json())



