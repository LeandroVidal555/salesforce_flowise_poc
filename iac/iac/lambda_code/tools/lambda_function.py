from lambda_function_utils import *
import json


def lambda_handler(event, context):
    print("##### RECEIVED EVENT:", json.dumps(event))

    if "path" in event:
        print("Event came from API GW")

        endpoint = event["path"]
        print("Requested endpoint:", endpoint)
        print("Initiating parsing process...")

        payload_dict = json.loads(event["body"])
        print("Request payload:", payload_dict)

        if "action" not in payload_dict:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Unprocessable Entity",
                    "message": "Tool action identifier not specified."
                })
            }


        if payload_dict["action"] == "add_to_do":

            try:
                to_do_text = payload_dict["to_do_text"]
                assert isinstance(to_do_text, str), f"To do content must be a string, found: {type(to_do_text).__name__}"
                print(f"Adding new item to todo list: '{to_do_text}'")

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
                update_to_do_list(to_do_text)

                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Successfully updated to do list."
                    })
                }

            except Exception as e:
                print(f"Found error while updating the list: {e}")

                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "Internal server error",
                        "message": "Found error while updating the list. Please contact support."
                    })
                }
        else:
            print(f"Tool action unrecognized: {payload_dict["action"]}")

            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Unprocessable Entity",
                    "message": f"Tool action unrecognized: {payload_dict["action"]}"
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