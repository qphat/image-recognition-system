"""
RekognitionStack CDK
"""
# declare SQS that reacts to image upload SNS
# declare SNS to where it sends the items

from aws_cdk import (
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_apigateway as apigateway,
    aws_s3 as s3,
    Stack,
)
from constructs import Construct


class RekognitionStack(Stack):
    """
    RekognitionStack class is a CDK stack that
    creates a DynamoDB table, an SQS queue, and an SNS topic.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sqs_url: str,
        sqs_arn: str,
        sns_arn: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        iam.Role.customize_roles(
            self,
            use_precreated_roles={
                "RekognitionStack/image_recognition/ServiceRole": "cdk-rekognition-role",
                "RekognitionStack/ListImagesLambda/ServiceRole": "cdk-rekognition-role",
                "": "",
            },
        )

        # create DynamoDB table to hold Rekognition results
        table = ddb.Table(
            self,
            "Classifications",
            partition_key=ddb.Attribute(name="image", type=ddb.AttributeType.STRING),
        )

        # create Lambda function
        lambda_function = _lambda.Function(
            self,
            "image_recognition",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="image_recognition.handler",
            code=_lambda.Code.from_asset("recognition/runtime"),
            environment={
                "TABLE_NAME": table.table_name,
                "SQS_QUEUE_URL": sqs_url,
                "TOPIC_ARN": sns_arn,
            },
        )

        lambda_function.add_event_source_mapping(
            "ImgRekognitionLambda", event_source_arn=sqs_arn
        )

        # add additional API Gateway and lambda to list ddb
        list_img_lambda = _lambda.Function(
            self,
            "ListImagesLambda",
            function_name="ListImagesLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("recognition/runtime"),
            handler="list_images.handler",
            environment={"TABLE_NAME": table.table_name},
        )

        api = apigateway.RestApi(
            self,
            "REST_API",
            rest_api_name="List Images Service",
            cloud_watch_role=False,
            description="CW workshop - list images recognized from workshop.",
        )

        list_images = apigateway.LambdaIntegration(
            list_img_lambda,
            request_templates={"application/json": '{ "statusCode": "200" }'},
        )

        api.root.add_method("GET", list_images)

        table.grant_read_data(list_img_lambda)
