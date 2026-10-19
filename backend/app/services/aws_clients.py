"""
Single place that builds every boto3 client/resource used in this app.

Why this matters: it's the ONE spot that knows about AWS_ENDPOINT_URL
(LocalStack, for fake-data testing) vs. real AWS. Every service module
imports from here instead of calling boto3 directly, so swapping
fake -> real AWS never touches business logic.
"""
import boto3
from botocore.config import Config

from app.config import get_settings


def _common_kwargs() -> dict:
    settings = get_settings()
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return kwargs


def get_s3_client():
    return boto3.client("s3", **_common_kwargs())


def get_dynamodb_resource():
    return boto3.resource("dynamodb", **_common_kwargs())


def get_secrets_manager_client():
    return boto3.client("secretsmanager", **_common_kwargs())


def get_bedrock_runtime_client():
    """
    Bedrock is deliberately NOT routed through AWS_ENDPOINT_URL (LocalStack can't
    fake model invocation). Credential priority:
      1. BEDROCK_ACCESS_KEY_ID / BEDROCK_SECRET_ACCESS_KEY (real keys, used in
         docker-compose fake-data mode where AWS_ACCESS_KEY_ID is a fake value)
      2. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, only when NOT pointed at LocalStack
      3. boto3's default chain (IAM role / IRSA on EKS)
    """
    settings = get_settings()
    kwargs: dict = {"region_name": settings.BEDROCK_REGION}
    if settings.BEDROCK_ACCESS_KEY_ID and settings.BEDROCK_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.BEDROCK_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.BEDROCK_SECRET_ACCESS_KEY
    elif not settings.AWS_ENDPOINT_URL and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    # boto3 itself reads the AWS_ENDPOINT_URL env var and applies it to EVERY client,
    # which would silently send Bedrock calls to LocalStack. Explicitly ignore it.
    kwargs["config"] = Config(ignore_configured_endpoint_urls=True)
    return boto3.client("bedrock-runtime", **kwargs)
