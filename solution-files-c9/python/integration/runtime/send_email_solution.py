from xml.etree.ElementTree import Element, tostring
import requests
import boto3


def get_thirdparty_endpoint():
    '''
    Get thirdparty endpoint from SSM Parameter Store
    '''
    ssm_client = boto3.client('ssm', region_name='us-east-1')
    response = ssm_client.get_parameter(
        Name='thirdparty_endpoint', WithDecryption=False)
    return response['Parameter']['Value']


#1 Convert JSON data to XML string
def json_to_xml(event):
    root = Element('root')
    for key, value in event.items():
        child = Element(key)
        child.text = str(value)
        root.append(child)
    return tostring(root)


#2 Send XML string with HTTP POST
def post_xml(xml_string):
    endpoint = get_thirdparty_endpoint()
    headers = {'Content-Type': 'application/xml'}
    response = requests.post(get_thirdparty_endpoint(),
                             data=xml_string, headers=headers)
    return response


def handler(event, context):

    # call method #1 with var "event" to convert json to xml
    xml_string = json_to_xml(event)
    print(xml_string)

    # call method #2 to post xml
    response = post_xml(xml_string)
    print(response)

    return {
        'statusCode': 200,
        "message": "Success!"
    }
