from unittest.mock import patch

from app.config import Settings
from app.services.aws_clients import get_bedrock_runtime_client


def _run(**overrides):
    settings = Settings(_env_file=None, **overrides)
    with patch("app.services.aws_clients.get_settings", return_value=settings), patch(
        "app.services.aws_clients.boto3.client"
    ) as mock_client:
        get_bedrock_runtime_client()
    return mock_client.call_args.kwargs


def test_dedicated_bedrock_keys_win_even_in_localstack_mode():
    kwargs = _run(
        AWS_ENDPOINT_URL="http://localstack:4566",
        AWS_ACCESS_KEY_ID="fake-access-key",
        AWS_SECRET_ACCESS_KEY="fake-secret-key",
        BEDROCK_ACCESS_KEY_ID="REAL",
        BEDROCK_SECRET_ACCESS_KEY="REALSECRET",
    )
    assert kwargs["aws_access_key_id"] == "REAL"
    assert kwargs["aws_secret_access_key"] == "REALSECRET"


def test_fake_localstack_keys_are_never_sent_to_bedrock():
    kwargs = _run(
        AWS_ENDPOINT_URL="http://localstack:4566",
        AWS_ACCESS_KEY_ID="fake-access-key",
        AWS_SECRET_ACCESS_KEY="fake-secret-key",
    )
    assert "aws_access_key_id" not in kwargs


def test_real_aws_mode_falls_back_to_regular_keys():
    kwargs = _run(AWS_ACCESS_KEY_ID="AKIAREAL", AWS_SECRET_ACCESS_KEY="secret")
    assert kwargs["aws_access_key_id"] == "AKIAREAL"
