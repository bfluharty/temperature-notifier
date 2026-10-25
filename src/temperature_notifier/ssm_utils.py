"""Small, typed helpers for reading and updating SSM parameters."""

import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_ssm_client() -> Any:
    """Create one SSM client per execution environment and reuse it."""
    return boto3.client("ssm")


def get_value(parameter_name: str, *, with_decryption: bool = True) -> str:
    """Return a parameter value, converting AWS failures to a useful error."""
    logger.debug("Getting SSM parameter: %s", parameter_name)
    try:
        response = _get_ssm_client().get_parameter(
            Name=parameter_name,
            WithDecryption=with_decryption,
        )
        value = response["Parameter"]["Value"]
    except (ClientError, KeyError, TypeError) as error:
        raise RuntimeError(
            f"Unable to retrieve SSM parameter {parameter_name}"
        ) from error

    logger.debug("SSM parameter retrieved successfully: %s", parameter_name)
    return value


def set_value(parameter_name: str, value: str) -> None:
    """Overwrite a String parameter with ``value``."""
    logger.debug("Setting SSM parameter: %s", parameter_name)
    try:
        _get_ssm_client().put_parameter(
            Name=parameter_name,
            Value=value,
            Type="String",
            Overwrite=True,
        )
    except ClientError as error:
        raise RuntimeError(
            f"Unable to update SSM parameter {parameter_name}"
        ) from error

    logger.debug("SSM parameter updated successfully: %s", parameter_name)
