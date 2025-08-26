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
        # Kiểm tra nếu request thành công (status code 200)
        response.raise_for_status() 
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from URL {url}: {e}")
        return None # Trả về None nếu có lỗi

#2 Create a function to upload the file to s3 and print any exception.
def upload_image_to_s3(bucket, key, data):
    """
    Uploads an image to S3
    """
    if data is None: # Không tải lên nếu dữ liệu rỗng
        print("No data to upload to S3.")
        return False
    try:
        print(f"Uploading image to S3 bucket: {bucket} with key: {key}")
        s3_client.put_object(Body=data, Bucket=bucket, Key=key)
        print("Image uploaded successfully!")
        return True
    except botocore.exceptions.ClientError as e:
        print("Error uploading image to S3")
        print(e)
        return False


def handler(event, context):
    # Kiểm tra xem queryStringParameters có tồn tại không
    if "queryStringParameters" not in event:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing queryStringParameters in the event.')
        }

    url = event["queryStringParameters"].get("url")
    name = event["queryStringParameters"].get("name")

    # Kiểm tra các tham số cần thiết
    if not url or not name:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing "url" or "name" in queryStringParameters.')
        }

    # call method #1 to download image
    data = get_file_from_url(url)

    if data is None:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Failed to download image from {url}')
        }

    # call method #2 to upload image to s3
    success = upload_image_to_s3(S3_BUCKET, name, data)
    
    if success:
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully Uploaded Img!')
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to upload image to S3.')
        }