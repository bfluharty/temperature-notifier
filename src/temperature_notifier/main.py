"""Temperature forecast evaluation and notification workflow."""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from . import config_loader
from .constants import (
    BATTERIES_INSIDE_PARAMETER,
    FORECAST_TIMEZONE,
    FORECAST_URL,
    LATITUDE_PARAMETER,
    LONGITUDE_PARAMETER,
    REQUEST_TIMEOUT_SECONDS,
    SLACK_WEBHOOK_PARAMETER,
    STATE_INSIDE,
    STATE_OUTSIDE,
    TEMPERATURE_UNIT,
)
from .ssm_utils import get_value, set_value

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_forecast() -> dict[str, Any]:
    """Fetch the hourly forecast for the configured coordinates."""
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": get_value(LATITUDE_PARAMETER),
            "longitude": get_value(LONGITUDE_PARAMETER),
            "hourly": "temperature_2m",
            "temperature_unit": TEMPERATURE_UNIT,
            "timezone": FORECAST_TIMEZONE,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def notify_slack(message: str) -> None:
    """Send one notification to the configured Slack webhook."""
    response = requests.post(
        get_value(SLACK_WEBHOOK_PARAMETER),
        json={"text": message},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def _current_forecast_hour(utc_offset_seconds: int, now: datetime | None = None) -> str:
    """Return the provider's local forecast-hour key for the current moment."""
    current_utc = now or datetime.now(UTC)
    local_time = current_utc + timedelta(seconds=utc_offset_seconds)
    return local_time.strftime("%Y-%m-%dT%H:00")


def _forecast_temperatures(
    forecast: Mapping[str, Any], forecast_length: int, now: datetime | None = None
) -> list[float]:
    """Select the configured number of temperatures beginning at the local hour."""
    try:
        hourly = forecast["hourly"]
        times = hourly["time"]
        temperatures = hourly["temperature_2m"]
        utc_offset_seconds = int(forecast["utc_offset_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "Forecast response is missing required hourly data"
        ) from error

    try:
        starting_index = times.index(
            _current_forecast_hour(utc_offset_seconds, now=now)
        )
    except (AttributeError, ValueError) as error:
        raise RuntimeError("Current forecast hour was not returned") from error

    selected = temperatures[starting_index : starting_index + forecast_length]
    if not selected:
        raise RuntimeError("Forecast contains no temperatures for the requested window")
    return selected


def _action_for_conditions(
    inside_state: str, minimum: float, maximum: float, config: config_loader.Config
) -> tuple[str, str | None]:
    """Return the notification and optional state transition for current conditions."""
    lower_bound = config.temperature.min
    upper_bound = config.temperature.max

    if inside_state == STATE_OUTSIDE and (
        minimum < lower_bound or maximum > upper_bound
    ):
        return "Bring in batteries", STATE_INSIDE

    if inside_state == STATE_INSIDE and (
        minimum >= lower_bound and maximum <= upper_bound
    ):
        return "Take out batteries", STATE_OUTSIDE

    return "No action needed", None


def decide_action(
    today_min_temp: float, today_max_temp: float, config: config_loader.Config
) -> None:
    """Notify Slack and persist state when the temperature requires a transition."""
    inside_state = get_value(BATTERIES_INSIDE_PARAMETER, with_decryption=False)
    message, next_state = _action_for_conditions(
        inside_state, today_min_temp, today_max_temp, config
    )

    # Persist state only after Slack accepts the notification. This prevents a
    # failed notification from suppressing a later retry.
    notify_slack(message)
    if next_state is not None:
        set_value(BATTERIES_INSIDE_PARAMETER, next_state)
        logger.info("Battery state changed to %s", next_state)
    else:
        logger.info("No battery state change required")


def main() -> None:
    """Run one forecast evaluation and notification cycle."""
    config = config_loader.load_config()
    temperatures = _forecast_temperatures(get_forecast(), config.forecast_length)
    decide_action(min(temperatures), max(temperatures), config)


def lambda_handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for the EventBridge schedule."""
    del event, context  # The scheduled invocation does not need either value.
    logger.info("Starting temperature notification check")
    main()
    logger.info("Temperature notification check completed")
    return {"statusCode": 200, "body": "Temperature notification check completed."}


if __name__ == "__main__":
    main()
