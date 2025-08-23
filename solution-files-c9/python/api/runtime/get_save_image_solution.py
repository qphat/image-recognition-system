import os
import json
import boto3
import requests
import botocore.exceptions

s3_client = boto3.client("s3")
S3_BUCKET = os.getenv('BUCKET_NAME')

#1 Create function to download the content from a url without a filename and print any request exception.
def get_file_from_url(url):
    try:
        response = requests.get(url)
        return response.content
    except requests.exceptions.RequestException as e:
        print(e)

#2 Create a function to upload the file to s3 and print any exception.
def upload_image_to_s3(bucket, key, data):
    """
    Uploads an image to S3
    """
    try:
        print("Uploading image to S3")
        s3_client.put_object(Body=data, Bucket=bucket, Key=key)
        return True
    except botocore.exceptions.ClientError as e:
        print("Error uploading image to S3")
        print(e)
        return False


def handler(event, context):
    url = event["queryStringParameters"]["url"]
    name = event["queryStringParameters"]["name"]

    # call method #1 to download image
    data = get_file_from_url(url)

    # call mehtod #2 to upload image to s3
    upload_image_to_s3(S3_BUCKET, name, data)
    

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully Uploaded Img!')
    }

    