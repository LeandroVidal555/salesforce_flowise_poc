import json
import os
#import time
import re
from lambda_function_utils import *


# Get environment vars
extract_text = os.getenv("EXTRACT_TEXT").lower() == "true" # booleans come as strings




def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Extract information from the event
    pk = event['source']
    sk = event['time']
    subject = event['detail']['payload']['Action__c']
    # payload data does not come in any standard format, so it needs parsing
    data_parsed = re.findall(r"(\w+): '([^']*)'", event['detail']['payload']['Data__c'])
    data_dict = {key: value for key, value in data_parsed}
    doc_id = data_dict["Id"]
    rec_id = data_dict["record_id"]

    # Get file from SalesForce and insert in S3
    sf_token = sf_get_token()
    filename = dl_sf_file(doc_id, sf_token)
    extracted_text = None
    if extract_text and filename.endswith(("pdf","txt", "csv")): # TODO: add support for the rest of Unstructured file types
        extracted_text = sf_get_doc_text()
    upload_files_s3(rec_id, doc_id, filename)
    
    # Prepare and insert DynamoDB item
    if extracted_text:
        item = {
            'pk': pk,
            'sk': sk,
            'subject': subject, 
            'extractedText': extracted_text
        }
        insert_item_dynamodb(item)

    # Interact with Flowise API
    fw_api_key = fw_get_api_key()
    load_process_upsert(rec_id, fw_api_key)