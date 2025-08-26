import os
import boto3
import json
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

# Khởi tạo client DynamoDB
dynamodb_client = boto3.client("dynamodb")
table_name = os.environ.get("TABLE_NAME")

# Kiểm tra biến môi trường
if not table_name:
    raise ValueError("TABLE_NAME environment variable is not set")

# Khởi tạo đối tượng TypeDeserializer
deserializer = TypeDeserializer()

def _deserialize_item(item):
    """
    Chuyển đổi một mục DynamoDB từ định dạng DynamoDB sang định dạng Python
    """
    return {k: deserializer.deserialize(v) for k, v in item.items()}

# 1. Tạo hàm để quét và liệt kê tất cả các mục từ bảng DynamoDB
def scan_all_items(table_name, limit=None, start_key=None):
    """
    Quét toàn bộ bảng DynamoDB, xử lý phân trang và trả về tất cả các mục.
    Args:
        table_name (str): Tên bảng DynamoDB
        limit (int, optional): Giới hạn số mục trả về
        start_key (dict, optional): Key để bắt đầu phân trang
    """
    items = []
    try:
        kwargs = {"TableName": table_name}
        if limit:
            kwargs["Limit"] = min(limit, 1000)  # Giới hạn tối đa 1000 theo API DynamoDB
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key

        response = dynamodb_client.scan(**kwargs)
        items.extend(response.get("Items", []))

        # Xử lý phân trang
        while 'LastEvaluatedKey' in response and (not limit or len(items) < limit):
            kwargs["ExclusiveStartKey"] = response['LastEvaluatedKey']
            response = dynamodb_client.scan(**kwargs)
            items.extend(response.get("Items", []))
            if limit and len(items) >= limit:
                items = items[:limit]
                break

        # Chuyển đổi sang định dạng Python
        deserialized_items = [_deserialize_item(item) for item in items]
        return {
            "items": deserialized_items,
            "last_evaluated_key": response.get("LastEvaluatedKey")
        }
    except ClientError as e:
        print(f"DynamoDB error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

def handler(event, context):
    try:
        # Lấy tham số từ event (nếu có)
        limit = event.get("queryStringParameters", {}).get("limit")
        start_key = event.get("queryStringParameters", {}).get("start_key")
        limit = int(limit) if limit and limit.isdigit() else None
        start_key = json.loads(start_key) if start_key else None

        # Gọi phương thức để quét các mục từ DynamoDB
        result = scan_all_items(table_name, limit=limit, start_key=start_key)

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "DynamoDB table not found"})
            }
        print(f"DynamoDB error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve items from DynamoDB"})
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An unexpected error occurred"})
        }