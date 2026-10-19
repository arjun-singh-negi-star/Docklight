import os

import fakeredis
import pytest
from moto import mock_aws

os.environ.setdefault("PINECONE_API_KEY", "test-key")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "test-table")
os.environ.setdefault("USERS_TABLE_NAME", "test-users")
os.environ.setdefault("CONVERSATIONS_TABLE_NAME", "test-conversations")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")


@pytest.fixture
def aws_mock():
    with mock_aws():
        yield


@pytest.fixture
def fake_redis():
    from app.services.redis_client import reset_redis_client_for_tests

    client = fakeredis.FakeStrictRedis(decode_responses=True)
    reset_redis_client_for_tests(client)
    yield client
