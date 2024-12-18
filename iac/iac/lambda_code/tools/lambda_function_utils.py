import os
from openpyxl import load_workbook
import boto3
from datetime import datetime



# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")


# Initialize S3 client
s3 = boto3.client("s3")



def update_to_do_list(to_do_text):
    object_key = "flowise_tools/to_do_list.xlsx"
    local_file_name = object_key.split("/")[-1]
    local_file_path = f"/tmp/{local_file_name}"

    # Download the file from S3
    s3.download_file(bucket_name, object_key, local_file_path)
    print(f"Downloaded {object_key} from {bucket_name} to {local_file_path}")

    # Edit the file using openpyxl
    workbook = load_workbook(local_file_path)
    sheet = workbook.active

    new_row = [to_do_text, datetime.now().strftime("%Y/%m/%d-%H:%M:%S")]
    sheet.append(new_row)

    workbook.save(local_file_path)
    print("New row added and file saved locally.")

    # Upload the updated file back to S3
    s3.upload_file(local_file_path, bucket_name, object_key)
    print(f"Updated file uploaded back to s3://{bucket_name}/{object_key}")