from xml.etree.ElementTree import Element, ElementTree, tostring
import requests
import boto3
import json


def get_thirdparty_endpoint():
    '''
    Get thirdparty endpoint from SSM Parameter Store
    '''
    ssm_client = boto3.client('ssm', region_name='us-east-1')
    response = ssm_client.get_parameter(
        Name='thirdparty_endpoint', WithDecryption=False)
    return response['Parameter']['Value']

# 1. Convert JSON data to XML string
def convert_json_to_xml(json_data):
    """
    Converts a JSON object to an XML string.
    """
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
    # Return a byte string with a specified encoding
    return tostring(root, encoding='utf-8', method='xml')


# 2. Send XML string with HTTP POST
def send_xml_with_post(xml_string):
    """
    Sends an XML string to a third-party endpoint using HTTP POST.
    """
    endpoint = get_thirdparty_endpoint()
    headers = {'Content-Type': 'application/xml'}
    response = requests.post(endpoint, data=xml_string, headers=headers)
    response.raise_for_status() # Raise an HTTPError if the HTTP request returned an unsuccessful status code
    return response.status_code


def handler(event, context):
    try:
        # call method #1 with var "event" to convert json to xml
        xml_data = convert_json_to_xml(event)

        if xml_data:
            # call method #2 to post xml
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

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {
            'statusCode': 500,
            'message': f"Request failed: {e}"
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'message': f"An unexpected error occurred: {e}"
        }
