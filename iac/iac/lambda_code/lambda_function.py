from lambda_function_utils import *
import json
import re
import time

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    if "httpMethod" in event:
        print("Event came from API.")

        endpoint = event["path"]
        print("Requested endpoint:", endpoint)

        data_dict = json.loads(event['body'])
        print("Request body:", data_dict)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success.",
                "data": data_dict
            })
        }
    
    elif "source" in event:
        print("Event came from SalesForce.")
        # Extract information from the event
        #   payload data does not come in any standard format, so it needs parsing
        action = event['detail']['payload']['Action__c']
        data_parsed = re.findall(r"(\w+): '([^']*)'", event['detail']['payload']['Data__c'])
        data_dict = {key: value for key, value in data_parsed}

        if action == "ImportFile":
            print(f"{action} action in SF. Initiating download, parse and insert process...")
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

        elif action == "ImportText":
            print(f"{action} action in SF. Initiating parse and insert process...")
            text = data_dict["text"]
            rec_id = data_dict["record_id"]

            # Create text file
            create_text_file(text)

            # Upload file to S3
            epoch_ms = int(time.time() * 1000)
            filename = f"sftxt_{epoch_ms}.txt"
            file_path = upload_files_s3(rec_id, filename)

            # Interact with Flowise API for vector data upsertion
            fw_api_key = fw_get_api_key()
            load_process_upsert(file_path, filename, rec_id, fw_api_key)


        else:
            print(f"Action type unrecognized: {action}")
            sys.exit(1)
    
    else:
        print("Event source unrecognized.")

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Unprocessable Entity",
                "message": "Event source unrecognized."
            })
        }
