import os
import boto3
import json
from boto3.dynamodb.types import TypeDeserializer

# Khởi tạo client DynamoDB
dynamodb_client = boto3.client("dynamodb")
table_name = os.environ["TABLE_NAME"]

# Khởi tạo đối tượng TypeDeserializer để chuyển đổi dữ liệu DynamoDB về định dạng Python
deserializer = TypeDeserializer()

def _deserialize_item(item):
    """
    Chuyển đổi một mục DynamoDB từ định dạng DynamoDB sang định dạng Python
    """
    return {k: deserializer.deserialize(v) for k, v in item.items()}

# 1. Tạo hàm để quét và liệt kê tất cả các mục từ bảng DynamoDB
def scan_all_items(table_name):
    """
    Quét toàn bộ bảng DynamoDB, xử lý phân trang và trả về tất cả các mục.
    """
    items = []
    response = dynamodb_client.scan(
        TableName=table_name
    )
    items.extend(response.get("Items", []))

    # Xử lý phân trang nếu có nhiều hơn 1MB dữ liệu
    while 'LastEvaluatedKey' in response:
        response = dynamodb_client.scan(
            TableName=table_name,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get("Items", []))
    
    # Chuyển đổi các mục từ định dạng DynamoDB sang định dạng Python
    deserialized_items = [_deserialize_item(item) for item in items]

    return deserialized_items

def handler(event, context):
    try:
        # Gọi phương thức để quét các mục từ DynamoDB và lưu vào biến response.
        response_items = scan_all_items(table_name)
        
        return {
            "statusCode": 200,
            "body": json.dumps(response_items)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve items from DynamoDB"})
        }