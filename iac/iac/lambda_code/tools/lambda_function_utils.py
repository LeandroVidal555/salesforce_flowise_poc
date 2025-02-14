import os
from openpyxl import load_workbook
import boto3
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")
email_sender = os.getenv("EMAIL_SENDER")
secret_gmail_app_pass_name = os.getenv("SECRET_GMAIL_APP_PASS_NAME")


# Initialize the SecretsManager client
sm = boto3.client('secretsmanager')
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



def send_email(email_subject, email_body, email_recipient):
    # Gmail SMTP server details
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465  # SSL port
    
    # Your Gmail credentials (for production, store these securely)
    password = sm.get_secret_value(SecretId=secret_gmail_app_pass_name)["SecretString"]  # Use an app-specific password if you have 2FA enabled
    
    # Create the email message
    message = MIMEMultipart("alternative")
    message['Subject'] = email_subject
    message['From'] = email_sender
    message['To'] = email_recipient

    # Create the plain-text and HTML version of your message
    text = "Hello,\nThis is a test email sent from AWS Lambda using your Gmail account."
    html = """\
    <html>
      <body>
        <p>Hello,<br>
           This is a test email sent from AWS Lambda using your Gmail account.
        </p>
      </body>
    </html>
    """

    # Attach parts into message container.
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    # Send the email via Gmail's SMTP server using SSL
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(email_sender, password)
        server.sendmail(email_sender, email_recipient, message.as_string())