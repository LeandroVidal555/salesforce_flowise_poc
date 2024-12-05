from lambda_function_utils import *
import json
import time


def lambda_handler(event, context):
    print("##### RECEIVED EVENT:", json.dumps(event))

    if "path" in event:
        print("Event came from API GW. Initiating parse and insert process...")

        endpoint = event["path"]
        print("Requested endpoint:", endpoint)

        try:
            payload_dict = json.loads(event["body"])["payload"]
            print("Request payload:", payload_dict)

            text = payload_dict["graphText"]
            rec_id = payload_dict["record_id"]

            # Create text file
            create_text_file(text)

            # Upload file to S3
            epoch_ms = int(time.time() * 1000)
            filename = f"graphtxt_{epoch_ms}.txt"

        except Exception as e:
            print(f"Found error while processing the data: {e}")

            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Payload error",
                    "message": f"Found error while processing the data: {e}"
                })
            }

        try:
            file_path = upload_files_s3(rec_id, filename)

            # Interact with Flowise API for vector data upsertion
            fw_api_key = fw_get_api_key()
            load_process_upsert(file_path, filename, rec_id, fw_api_key)

        except Exception as e:
            print(f"Found error while uploading/upserting the data: {e}")

            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Internal server error",
                    "message": "Found error while upserting the data. Please contact support."
                })
            }

    
    else:
        print("Event source unrecognized.")

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Unprocessable Entity",
                "message": "Event source unrecognized."
            })
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Success."
        })
    }