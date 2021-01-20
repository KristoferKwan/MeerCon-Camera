import os
import boto3
from dotenv import load_dotenv

# OR, explicitly providing path to '.env'
from pathlib import Path  # Python 3.6+ only
env_path = Path('.') / 'storage.env'
load_dotenv(dotenv_path=env_path)

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME = os.getenv('BUCKET_NAME')

session = boto3.Session(
   aws_access_key_id=AWS_ACCESS_KEY_ID,
   aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

def download_image_to_s3(complete_file_path, key):
    """
    Downloads a file from AWS S3.:
    """
    if complete_file_path is None:
        raise ValueError("Please enter a valid and complete file path")

    s3 = session.client('s3')
    with open(complete_file_path, 'wb') as f:
        s3.download_fileobj(AWS_BUCKET_NAME, key, f)


def upload_file_to_s3(complete_file_path, key):
   """
   Uploads a file to AWS S3.:
   """
   if complete_file_path is None:
       raise ValueError("Please enter a valid and complete file path")

   s3 = session.resource('s3')
   data = open(os.path.normpath(complete_file_path), 'rb')
   s3.Bucket(AWS_BUCKET_NAME).put_object(Key=key, Body=data)