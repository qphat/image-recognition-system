from constructs import Construct
from aws_cdk import Duration, Stack
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_iam as iam
from aws_cdk import aws_cognito as cognito
from aws_cdk import CfnOutput

class APIStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket để lưu ảnh
        bucket = s3.Bucket(self, "CW-Workshop-Images")

        # Import bucket chứa Lambda layer
        asset_bucket = s3.Bucket.from_bucket_name(
            scope=self,
            id="lamba_layer_zipfile",
            bucket_name="lab-resources-f4af59b0",
        )
        requests_layer_file = "requests_layer3_11.zip"

        # Lambda Layer (requests lib)
        requests = lambda_.LayerVersion(
            self,
            "requests_layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            layer_version_name="requests_layer",
            code=lambda_.S3Code(bucket=asset_bucket, key=requests_layer_file),
        )

        # IAM Role cho Lambda
        lambda_role = iam.Role(
            self,
            "ImageLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        bucket.grant_read_write(lambda_role)

        # Lambda function
        image_get_and_save_lambda = lambda_.Function(
            self,
            "ImageGetAndSaveLambda",
            function_name="ImageGetAndSaveLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            layers=[requests],
            code=lambda_.Code.from_asset("api/runtime"),
            handler="get_save_image.handler",
            environment={"BUCKET_NAME": bucket.bucket_name},
            role=lambda_role,
            timeout=Duration.seconds(60),  # Tăng timeout nếu cần
        )

        # Cognito User Pool
        user_pool = cognito.UserPool(
            self,
            "APIUserPool",
            user_pool_name="APIUserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(username=True, email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
        )

        # User Pool Client
        user_pool_client = user_pool.add_client(
            "APIUserPoolClient",
            auth_flows=cognito.AuthFlow(
                admin_user_password=True,
                user_password=True,
                user_srp=True,
            ),
        )

        # API Gateway
        api = apigateway.RestApi(
            self,
            "REST_API",
            rest_api_name="Image Upload Service",
            cloud_watch_role=False,
            description="CW workshop - upload image for workshop.",
        )

        # Tích hợp Lambda
        get_image_integration = apigateway.LambdaIntegration(image_get_and_save_lambda)

        # Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "APIGatewayCognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        # Method GET có xác thực Cognito
        api.root.add_method(
            "GET",
            get_image_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        # SQS Queue
        upload_queue = sqs.Queue(
            self, id="uploaded_image_queue", visibility_timeout=Duration.seconds(60)
        )
        self.upload_queue_url = upload_queue.queue_url
        self.upload_queue_arn = upload_queue.queue_arn

        # SNS Topic + subscription SQS
        upload_event_topic = sns.Topic(self, id="uploaded_image_topic")
        sqs_subscription = sns_subs.SqsSubscription(upload_queue, raw_message_delivery=True)
        upload_event_topic.add_subscription(sqs_subscription)

        # Gắn event notification cho bucket
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT, s3n.SnsDestination(upload_event_topic)
        )

        # Output thông tin
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "ApiUrl", value=api.url)

    @property
    def sqs_url(self) -> str:
        return self.upload_queue_url

    @property
    def sqs_arn(self) -> str:
        return self.upload_queue_arn