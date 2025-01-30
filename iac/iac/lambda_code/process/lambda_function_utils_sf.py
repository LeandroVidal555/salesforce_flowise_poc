import json
import os
import re
import requests
import sys
import urllib.parse
import boto3


# Get environment vars
env = os.getenv("ENV")
secret_sf_creds_name = os.getenv("SECRET_SF_CREDS_NAME")
base_url_sf = os.getenv("BASE_URL_SF")
file_download_path = os.getenv("FILE_DOWNLOAD_PATH")
supported_formats = json.loads(os.getenv("SUPPORTED_FORMATS"))
supported_formats_img = json.loads(os.getenv("SUPPORTED_FORMATS_IMG"))
supported_formats_all = supported_formats + supported_formats_img


# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')



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
        print(f"Failed to retrieve token: {res.status_code} {res.reason}")
        sys.exit(1)
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
    res = requests.head(url_download, headers = {"Content-Type": "application/json", "Authorization":"Bearer " + token})
    
    if res.status_code != 200:
        print(f"Failed to get headers for file: {res.status_code} {res.reason}")
        sys.exit(1)

    filename = re.search(r'filename="(.+)"', res.headers["Content-Disposition"]).group(1)

    filename_decoded = urllib.parse.unquote(filename)
    filename_base, filename_ext = os.path.splitext(filename_decoded)
    file_size = int(res.headers["Content-Length"])
    
    #filetype = res.headers.get("Content-Type")
    #print(f"Content-Type: {filetype}")

    if filename_ext not in supported_formats_all:
        print(f"Unsupported file extension: {filename_ext}")
        sys.exit(1)

    if file_size > 10 * 1024 * 1024:
        print(f"File exceeded 10MB size imit: {file_size / 1024 / 1024} MB")
        sys.exit(1)

    res = requests.get(url_download, headers = {"Content-Type": "application/json", "Authorization":"Bearer " + token})

    if res.status_code != 200:
        print(f"Failed to download file: {res.status_code} {res.reason}")
        sys.exit(1)
    
    print(f"Saving file: {filename_decoded} as generic /tmp/download...")
    with open(f"/tmp/download", "wb") as file:
        # Use iter_content to write the file in chunks
        for chunk in res.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                file.write(chunk)
    
    return filename