import os
import requests


# Get environment vars
api_ep = os.getenv("API_EP")




def create_text_file(text):
    print("Creating text file with the text included in the event...")
    with open("/tmp/event.txt", 'w') as f:
        f.write(text)



def upload_files_s3(rec_id, filename, doc_id=None):

    if doc_id is None:
        print("Uploading generated event text file...")
        try:
            file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename}"
            s3.upload_file("/tmp/event.txt", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")

    else:
        filename_decoded = urllib.parse.unquote(filename)
        filename_base, filename_ext = os.path.splitext(filename_decoded)

        # Upload the file - flowise (general)
        print("Uploading original file...")
        if not filename_base.startswith("sffile_"):
            filename_base = "sffile_" + filename_base
        try:
            file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename_base}_{doc_id}{filename_ext}"
            s3.upload_file("/tmp/download", bucket_name, file_path)
            print(f"File {file_path} uploaded to {bucket_name}")
        except Exception as e:
            print(f"Found error while uploading {file_path}: {e}")

        # Upload the file - flowise (image extracted text)
        if filename_ext in supported_formats_img:
            print("Uploading image file's extracted text for upsertion...")
            with open("/tmp/image.txt", 'w') as f:
                txt_file = pytesseract.image_to_string(Image.open("/tmp/download"))
                f.write(txt_file)
            try:
                file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename_base}_{doc_id}.txt".replace("sffile", "sfimg")
                s3.upload_file("/tmp/image.txt", bucket_name, file_path)
                print(f"File {file_path} uploaded to {bucket_name}")
            except Exception as e:
                print(f"Found error while uploading {file_path}: {e}")
        elif filename_ext == ".xlsx":
            print("Uploading xslx file's extracted csv for upsertion...")
            os.rename("/tmp/download", "/tmp/download.xlsx") # openpyxl requires an extension
            wb = load_workbook("/tmp/download.xlsx")
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                # Open the output CSV file
                with open(f"/tmp/excel_{sheet_name}.csv", 'w', newline="") as f:
                    writer = csv.writer(f)
                    # Write the rows of the sheet
                    for row in sheet.iter_rows(values_only=True):
                        writer.writerow(row)
                try:
                    file_path = f"{bucket_path_fw_ds}/{rec_id}/{filename_base}_{doc_id}_{sheet_name}.csv".replace("sffile", "sfxl")
                    s3.upload_file(f"/tmp/excel_{sheet_name}.csv", bucket_name, file_path)
                    print(f"File {file_path} uploaded to {bucket_name}")
                except Exception as e:
                    print(f"Found error while uploading {file_path}: {e}")
                    sys.exit(1)

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

    # if it's an excel file, use a prefix that will match all the file's sheets
    if orig_filename.endswith(".xlsx"):
        file_path = "_".join(file_path.split("_")[:-1])
        file_path_source = file_path + ".xlsx"
    else:
        file_path_source = "/".join(file_path.split("/")[1:])
    
    # DUPLICATE CHECK
    #pgres_solve_duplicate(file_path_source)
    
    # UPSERT VECTOR DATA
    print("Upserting vector data...")
    try:
        res = requests.post(
            f"https://{cf_distro_domain}/api/v1/vector/upsert/{chatflow["id"]}",
            headers={"Authorization":f"Bearer {fw_api_key}","Content-Type":"application/json"},
            json={"overrideConfig":{"prefix":f"{file_path}","metadata":{"source": file_path_source, "record_id": rec_id}}}
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



