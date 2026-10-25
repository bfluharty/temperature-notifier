from datetime import UTC, datetime, timedelta
import logging

import requests

import config_loader
from constants import FORECAST_URL, IS_INSIDE_PATH, LAT_PATH, LON_PATH, SLACK_URL_PATH
from ssm_utils import get_value, set_value

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_forecast():
    r = requests.get(FORECAST_URL, params={
        "latitude": get_value(LAT_PATH), "longitude": get_value(LON_PATH),
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit", "timezone": "auto",
    }, timeout=10)
    r.raise_for_status()
    return r.json()


def notify_slack(text):
    response = requests.post(get_value(SLACK_URL_PATH), json={"text": text}, timeout=10)
    response.raise_for_status()


def decide_action(today_min_temp, today_max_temp, config):
    MIN_ACCEPTABLE_TEMP = config.temperature.min
    MAX_ACCEPTABLE_TEMP = config.temperature.max
    IS_BATTERIES_INSIDE = get_value(IS_INSIDE_PATH, False)

    if IS_BATTERIES_INSIDE == "false" and (today_min_temp < MIN_ACCEPTABLE_TEMP or today_max_temp > MAX_ACCEPTABLE_TEMP):
        notify_slack("Bring in batteries")
        set_value(IS_INSIDE_PATH, "true")
        logger.info("Bring in batteries notification sent")
        return

    if IS_BATTERIES_INSIDE == "true" and (today_min_temp >= MIN_ACCEPTABLE_TEMP and today_max_temp <= MAX_ACCEPTABLE_TEMP):
        notify_slack("Take out batteries")
        set_value(IS_INSIDE_PATH, "false")
        logger.info("Take out batteries notification sent")
        return

    notify_slack("No action needed")


def main():
    config = config_loader.load_config()
    forecast = get_forecast()
    hourly = forecast["hourly"]
    local_now = datetime.now(UTC) + timedelta(seconds=forecast["utc_offset_seconds"])
    current_hour = local_now.strftime("%Y-%m-%dT%H:00")

    try:
        starting_index = hourly["time"].index(current_hour)
    except ValueError as error:
        raise RuntimeError(f"Current forecast hour {current_hour} was not returned") from error

    hourly = {key: value[starting_index:starting_index + config.forecast_length] for key, value in hourly.items()}

    decide_action(min(hourly["temperature_2m"]), max(hourly["temperature_2m"]), config)


def lambda_handler(event, context):
    """AWS Lambda entry point, suitable for an EventBridge schedule."""
    logger.info("Starting temperature notification check")
    main()
    logger.info("Temperature notification check completed")
    return {"statusCode": 200, "body": "Temperature notification check completed."}


if __name__ == "__main__":
    main()
