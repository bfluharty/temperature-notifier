from unittest.mock import Mock, call, patch

import pytest
from botocore.exceptions import ClientError

from temperature_notifier import ssm_utils


@pytest.fixture
def ssm_client():
    client = Mock()
    ssm_utils._get_ssm_client.cache_clear()
    with patch.object(ssm_utils.boto3, "client", return_value=client) as create_client:
        yield client, create_client
    ssm_utils._get_ssm_client.cache_clear()


def aws_error(message="SSM failure"):
    return ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": message}},
        "GetParameter",
    )


def test_get_value_reads_decrypted_parameter_and_reuses_client(ssm_client):
    client, create_client = ssm_client
    client.get_parameter.return_value = {"Parameter": {"Value": "50"}}

    assert ssm_utils.get_value("/temperature-notifier/lat") == "50"
    assert ssm_utils.get_value("/temperature-notifier/lon") == "50"

    client.get_parameter.assert_has_calls(
        [
            call(Name="/temperature-notifier/lat", WithDecryption=True),
            call(Name="/temperature-notifier/lon", WithDecryption=True),
        ]
    )
    create_client.assert_called_once_with("ssm")


def test_get_value_can_disable_decryption(ssm_client):
    client, _ = ssm_client
    client.get_parameter.return_value = {"Parameter": {"Value": "false"}}

    assert (
        ssm_utils.get_value("/temperature-notifier/is-inside", with_decryption=False)
        == "false"
    )
    client.get_parameter.assert_called_once_with(
        Name="/temperature-notifier/is-inside", WithDecryption=False
    )


def test_get_value_wraps_aws_errors(ssm_client):
    client, _ = ssm_client
    client.get_parameter.side_effect = aws_error()

    with pytest.raises(RuntimeError, match="Unable to retrieve SSM parameter"):
        ssm_utils.get_value("/temperature-notifier/lat")


def test_set_value_writes_string_parameter(ssm_client):
    client, _ = ssm_client

    ssm_utils.set_value("/temperature-notifier/is-inside", "true")

    client.put_parameter.assert_called_once_with(
        Name="/temperature-notifier/is-inside",
        Value="true",
        Type="String",
        Overwrite=True,
    )


def test_set_value_wraps_aws_errors(ssm_client):
    client, _ = ssm_client
    client.put_parameter.side_effect = aws_error()

    with pytest.raises(RuntimeError, match="Unable to update SSM parameter"):
        ssm_utils.set_value("/temperature-notifier/is-inside", "true")
