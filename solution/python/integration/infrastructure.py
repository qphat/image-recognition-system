import aws_cdk as cdk
from aws_cdk import Stack
from constructs import Construct
from aws_cdk import Duration
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as lambda_events
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam

class IntegrationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rekognized_queue = sqs.Queue(
            self, id="rekognized_image_queue", visibility_timeout=Duration.seconds(60)
        )

        sqs_subscription = sns_subs.SqsSubscription(
            rekognized_queue, raw_message_delivery=True
        )

        rekognized_event_topic = sns.Topic(self, id="rekognized_image_topic")

        self.rekognized_event_topic_arn = rekognized_event_topic.topic_arn
        rekognized_event_topic.add_subscription(sqs_subscription)

        asset_bucket = s3.Bucket.from_bucket_name(
            scope=self,
            id="lamba_layer_zipfile",
            bucket_name="lab-resources-f4af59b0",
        )

        requests_layer_file = "requests_layer3_11.zip"

        requests = lambda_.LayerVersion(
            self,
            "requests_layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            layer_version_name="requests_layer",
            code=lambda_.S3Code(bucket=asset_bucket, key=requests_layer_file),
        )

        # Định nghĩa IAM Role
        lambda_role = iam.Role(
            self,
            "IntegrationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["ses:SendEmail", "ses:SendRawEmail"],
            resources=["*"]  # Thay bằng ARN cụ thể nếu có
        ))
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:parameter/thirdparty_endpoint"]
        ))

        # Lambda function
        integration_lambda = lambda_.Function(
            self,
            "IntegrationLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            layers=[requests],
            role=lambda_role,
            handler="send_email.handler",
            code=lambda_.Code.from_asset("integration/runtime"),
            timeout=Duration.seconds(30),
        )

        # Thêm event source từ SQS
        integration_lambda.add_event_source(lambda_events.SqsEventSource(rekognized_queue))

    @property
    def sns_arn(self) -> str:
        return self.rekognized_event_topic_arn