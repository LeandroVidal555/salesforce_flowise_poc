from lambda_function_utils import *
import json
import os
import re


# Get environment vars
supported_formats = json.loads(os.getenv("SUPPORTED_FORMATS"))
supported_formats_img = json.loads(os.getenv("SUPPORTED_FORMATS_IMG"))
supported_formats_all = supported_formats + supported_formats_img



def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))

    # Extract information from the event
    #   payload data does not come in any standard format, so it needs parsing
    data_parsed = re.findall(r"(\w+): '([^']*)'", event['detail']['payload']['Data__c'])
    data_dict = {key: value for key, value in data_parsed}
    doc_id = data_dict["Id"]
    rec_id = data_dict["record_id"]

    # Get file from SalesForce and insert in S3
    sf_token = sf_get_token()
    filename = dl_sf_file(doc_id, sf_token)

    # Upload original file/s to S3  
    file_path = upload_files_s3(rec_id, doc_id, filename)

    # Interact with Flowise API for vector data upsertion
    fw_api_key = fw_get_api_key()
    load_process_upsert(file_path, filename, rec_id, fw_api_key)