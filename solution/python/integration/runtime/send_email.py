from xml.etree.ElementTree import Element, ElementTree, tostring
import requests
import boto3
import json

def get_thirdparty_endpoint():
    ssm_client = boto3.client('ssm', region_name='us-east-1')  # Nên dùng cdk.Aws.REGION
    response = ssm_client.get_parameter(
        Name='thirdparty_endpoint', WithDecryption=False)coginto
    return response['Parameter']['Value']

def convert_json_to_xml(json_data):
    if not json_data:
        return None
    root = Element('data')
    def create_xml_element(parent, data):
        if isinstance(data, dict):
            for key, value in data.items():
                element = Element(key)
                parent.append(element)
                create_xml_element(element, value)
        elif isinstance(data, list):
            for item in data:
                element = Element('item')
                parent.append(element)
                create_xml_element(element, item)
        else:
            parent.text = str(data)
    create_xml_element(root, json_data)
    return tostring(root, encoding='utf-8', method='xml')

def send_xml_with_post(xml_string):
    endpoint = get_thirdparty_endpoint()
    headers = {'Content-Type': 'application/xml'}
    response = requests.post(endpoint, data=xml_string, headers=headers, timeout=10)
    print(f"POST request to {endpoint} returned status {response.status_code}")
    response.raise_for_status()
    return response.status_code

def handler(event, context):
    try:
        for record in event.get('Records', []):
            json_data = json.loads(record.get('body', '{}'))
            xml_data = convert_json_to_xml(json_data)
            if xml_data:
                status_code = send_xml_with_post(xml_data)
                return {
                    'statusCode': status_code,
                    "message": "Success!"
                }
            else:
                return {
                    'statusCode': 400,
                    "message": "Bad Request: No JSON data to convert."
                }
    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'message': f"An unexpected error occurred: {e}"
        }