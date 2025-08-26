from aws_cdk import (
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_apigateway as apigateway,
    Stack,
)
from aws_cdk import aws_lambda_event_sources as events
from constructs import Construct
from aws_cdk import Duration

class RekognitionStack(Stack):
    """
    RekognitionStack CDK stack tạo DynamoDB, Lambda, API Gateway,
    và IAM Role cho các Lambda.
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

        # DynamoDB table
        table = ddb.Table(
            self,
            "Classifications",
            partition_key=ddb.Attribute(name="image", type=ddb.AttributeType.STRING),
        )

        # --- IAM ROLE for image_recognition Lambda ---
        recognition_role = iam.Role(
            self,
            "RekognitionLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        # Grant DynamoDB + SQS + SNS + Rekognition permissions
        table.grant_write_data(recognition_role)
        recognition_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:SendMessage",  # Thêm nếu cần
                ],
                resources=[sqs_arn],
            )
        )
        recognition_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[sns_arn],
            )
        )
        recognition_role.add_to_policy(
            iam.PolicyStatement(
                actions=["rekognition:DetectLabels"],
                resources=["*"],  # Thay bằng ARN cụ thể nếu có
            )
        )

        # Lambda for Rekognition
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
            role=recognition_role,
            timeout=Duration.seconds(30),  # Tăng timeout
        )

        # Event source mapping cho SQS (cần tạo Queue từ ARN nếu muốn dùng SqsEventSource)
        # Giả sử SQS queue đã tồn tại, dùng ARN để cấp quyền
        # Nếu cần tích hợp trực tiếp, cần import Queue từ stack khác
        # Ví dụ: từ stack khác, truyền queue object thay vì ARN

        # --- IAM ROLE for ListImagesLambda ---
        list_role = iam.Role(
            self,
            "ListImagesLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        table.grant_read_data(list_role)

        # Lambda để list images
        list_img_lambda = _lambda.Function(
            self,
            "ListImagesLambda",
            function_name="ListImagesLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("recognition/runtime"),
            handler="list_images.handler",
            environment={"TABLE_NAME": table.table_name},
            role=list_role,
        )

        # API Gateway
        api = apigateway.RestApi(
            self,
            "REST_API",
            rest_api_name="List Images Service",
            cloud_watch_role=False,
            description="CW workshop - list images recognized from workshop.",
        )

        list_images = apigateway.LambdaIntegration(list_img_lambda)

        api.root.add_method("GET", list_images)