from lambda_function_utils import *
from lambda_function_utils_sf import *
from lambda_function_utils_n4j import *
import json
import time
import boto3


# Initialize the SSM client
ssm = boto3.client('ssm')



def lambda_handler(event, context):
    print("##### RECEIVED EVENT:", json.dumps(event))

    if "path" in event:
        print("Event came from API GW.")

        endpoint = event["path"]
        print("Requested endpoint:", endpoint)

        data_dict = json.loads(event['body'])
        print("Request body:", data_dict)

        if "source" not in data_dict:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Unprocessable Entity",
                    "message": "Event source not specified."
                })
            }

        print("Source identificator:", data_dict["source"])

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "OK",
                "data": data_dict
            })
        }
    
    elif "source" in event:
        print("Event came from SalesForce.")
        # Extract information from the event
        #   payload data does not come in any standard format, so it needs parsing
        action = event['detail']['payload']['Action__c']
        data_dict = json.loads(event['detail']['payload']['Data__c'])
        rec_id = data_dict["record_id"]

        if action == "ImportFile":
            print(f"{action} action in SF. Initiating download, parse and insert process...")
            doc_id = data_dict["Id"]

            # Get file from SalesForce and insert in S3
            sf_token = sf_get_token()
            filename = dl_sf_file(doc_id, sf_token)

            # Upload original file/s to S3  
            file_path, file_path_full = upload_files_s3(rec_id, filename, doc_id)

        elif action == "ImportText":
            print(f"{action} action in SF. Initiating parse and insert process...")
            text = json.dumps(data_dict["text"])

            # Create text file
            create_text_file(text)

            # Upload file to S3
            epoch_ms = int(time.time() * 1000)
            filename = f"sftxt_{epoch_ms}.txt"
            file_path = upload_files_s3(rec_id, filename)

        else:
            print(f"Action type unrecognized: {action}")
            sys.exit(1)

        # Interact with Flowise API for vector data upsertion
        fw_api_key = fw_get_api_key()
        upsert_process(file_path, filename, rec_id, fw_api_key)

        send_text_n4j_enabled = ssm.get_parameter(Name=f"/{common_prefix}-{env}/pipeline/send_text_n4j")['Parameter']['Value']
        if send_text_n4j_enabled == "True" and action == "ImportFile":
            send_text_n4j(file_path_full)
    
    else:
        print("Event source unrecognized.")

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Unprocessable Entity",
                "message": "Event source unrecognized."
            })
        }
