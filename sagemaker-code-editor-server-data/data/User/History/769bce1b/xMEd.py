import os
import json
import boto3
import requests
import botocore.exceptions

s3_client = boto3.client("s3")
S3_BUCKET = os.getenv('BUCKET_NAME')

#1 Create function to download the content from a url without a filename and print any request exception.


#2 Create a function to upload the file to s3 and print any exception.

    

def handler(event, context):
    url = event["queryStringParameters"]["url"]
    name = event["queryStringParameters"]["name"]

    # call method #1 to download image

    # call method #2 to upload image to s3


    return {
        'statusCode': 200,
        'body': json.dumps('Successfully Uploaded Img!')
    }
