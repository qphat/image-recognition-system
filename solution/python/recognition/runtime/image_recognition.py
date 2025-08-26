import os
import boto3
import json

sqs = boto3.client("sqs")
rekognition = boto3.client("rekognition")
dynamodb = boto3.client("dynamodb")
sns = boto3.client("sns")

queue_url = os.environ["SQS_QUEUE_URL"]
table_name = os.environ["TABLE_NAME"]
topic_arn = os.environ["TOPIC_ARN"]

# 1 Use Rekognition to detect max of 10 labels with a confidence of 70 percent.
def detectImgLabels(bucket_name, key, maxLabels=10, minConfidence=70):
    image = {
        "S3Object": {
            "Bucket": bucket_name,
            "Name": key
        }
    }
    response = rekognition.detect_labels(Image=image, MaxLabels=maxLabels, MinConfidence=minConfidence)
    return response

# 2 Write labels to DynamoDB given a table name and item.
def writeToDynamoDb(tableName, item):
    dynamodb.put_item(
        TableName=tableName,
        Item=item
    )

# 3 Publish item to SNS
def triggerSNS(message):
    response = sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject="CodeWhisperer Workshop Success!", # Đã điều chỉnh Subject
    )
    print(response)

# 4 Delete message from SQS
def deleteFromSqs(receipt_handle):
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )


def handler(event, context):
    print(event)
    print(type(event))
    try:
        # process message from SQS
        for Record in event.get("Records", []): # Đảm bảo Records là một list
            receipt_handle = Record.get("receiptHandle")
            body_records = json.loads(Record.get("body", "{}")).get("Records", []) # Xử lý trường hợp body rỗng
            
            for record in body_records:
                bucket_name = record.get("s3", {}).get("bucket", {}).get("name") # Xử lý trường hợp key không tồn tại
                key = record.get("s3", {}).get("object", {}).get("key")

                # Bỏ qua nếu không lấy được bucket_name hoặc key
                if not bucket_name or not key:
                    print("Skipping record due to missing bucket name or key.")
                    continue

                # call method #1 to generate image label and store as var "labels"
                labels = detectImgLabels(bucket_name=bucket_name, key=key)
                print(f"Detected labels for {key}: {labels['Labels']}")

                # code snippet to create dynamodb item from labels
                db_result = []
                # Đảm bảo "Labels" tồn tại trước khi truy cập
                if "Labels" in labels:
                    json_labels = json.dumps(labels["Labels"])
                    db_labels = json.loads(json_labels)
                    for label in db_labels:
                        if "Name" in label:
                            db_result.append(label["Name"])
                
                db_item = {
                    "image": {"S": key},
                    "labels": {"S": str(db_result)}
                }

                # call method #2 to store "db_item" result on DynamoDB
                writeToDynamoDb(tableName=table_name, item=db_item)
                print(f"Wrote labels for {key} to DynamoDB.")

                # call method #3 sending db_result as a string to trigger SNS.
                triggerSNS(str(db_result))
                print(f"Published SNS message for {key}.")

                # call method #4 to delete img from SQS.
                deleteFromSqs(receipt_handle=receipt_handle)
                print(f"Deleted SQS message with handle: {receipt_handle}")

    except Exception as e:
        print(e)
        # Bắt lỗi chung, nhưng cũng cố gắng in ra thông tin chi tiết hơn nếu có thể
        print(f"Error processing records. Details: {e}")
        raise e