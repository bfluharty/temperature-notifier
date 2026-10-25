import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ssm_client = boto3.client("ssm")


def get_value(param_name: str, encrypted: bool = True) -> str:
    try:
        logger.debug("Getting SSM parameter: %s", param_name)
        response = ssm_client.get_parameter(Name=param_name, WithDecryption=encrypted)
        logger.debug("SSM parameter retrieved successfully")
        return response["Parameter"]["Value"]

    except ClientError as e:
        raise RuntimeError(f"Unable to retrieve SSM parameter {param_name}") from e


def set_value(param_name: str, value: str):
    try:
        logger.debug("Setting SSM parameter: %s", param_name)
        ssm_client.put_parameter(
            Name=param_name, Value=value, Type="String", Overwrite=True
        )
        logger.debug("SSM parameter updated successfully")

    except ClientError as e:
        raise RuntimeError(f"Unable to update SSM parameter {param_name}") from e
