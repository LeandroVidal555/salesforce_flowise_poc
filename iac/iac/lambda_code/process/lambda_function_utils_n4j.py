import json
import os
import requests
import sys
import boto3



# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")
secret_webapp_api_key_name = os.getenv("SECRET_WA_API_KEY_NAME")
supported_formats = json.loads(os.getenv("SUPPORTED_FORMATS"))
supported_formats_img = json.loads(os.getenv("SUPPORTED_FORMATS_IMG"))


# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')
# Initialize the S3 client
s3 = boto3.client('s3')
# Initialize the SSM client
ssm = boto3.client('ssm')



def get_xlsx_sheets():
    csv_file_paths = [os.path.join('/tmp', file) for file in os.listdir('/tmp') if file.endswith('.csv')]
    return csv_file_paths



def send_file(extension, file_name, cf_distro_domain, s3_uri, webapp_api_key, file):
    with open(file, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    if extension == ".xlsx":
        sheet_name = ''.join(file.split("/")[-1])
        print(f"Sending text for file: {file_name} - {sheet_name}...")
    else:
        print(f"Sending text for file: {file_name}...")

    try:
        res = requests.post(
            f"https://{cf_distro_domain}/api/aishit/analyseAndStoreText",
            headers={"Authorization": webapp_api_key, "Content-Type": "application/json"},
            json={"text": file_content, "resourceUrl": s3_uri}
        )

        if res.status_code == 200:
            print("Successfully sent text.")
        else:
            print(f"Found error while sending text. Got {res.status_code}: '{res.reason}'")
    except Exception as e:
        print(f"Found error while sending text: {e}")
        sys.exit(1)



def send_text_n4j(file_path_full):
    extension = os.path.splitext(file_path_full)[1].lower()
    file_name = ''.join(file_path_full.split("/")[-1])
    files_extracted = []

    if extension == ".xlsx": # XLSX files need per-sheet processing
        files_extracted = get_xlsx_sheets()
    elif extension in [".docx", ".pdf"] or extension in supported_formats_img: # these file formats need specific processing
        files_extracted.append("/tmp/extracted.txt")
    else: # every other supported format is in the end a text file
        files_extracted.append("/tmp/download")

    cf_distro_domain = ssm.get_parameter(Name=f"/{common_prefix}-{env}/pipeline/cf_distro_domain_webapp")['Parameter']['Value']

    s3_uri = f"s3://{bucket_name}/{file_path_full}"

    webapp_api_key = sm.get_secret_value(SecretId=secret_webapp_api_key_name)["SecretString"]

    # SEND TEXT TO N4J WEBAPP API
    for file_extracted in files_extracted:
        send_file(extension, file_name, cf_distro_domain, s3_uri, webapp_api_key, file_extracted)