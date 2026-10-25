"""Application constants shared by the forecast and notification workflow."""

from typing import Final

# SSM Parameter Store names.
SLACK_WEBHOOK_PARAMETER: Final[str] = "/temperature-notifier/slack-webhook-url"
LATITUDE_PARAMETER: Final[str] = "/temperature-notifier/lat"
LONGITUDE_PARAMETER: Final[str] = "/temperature-notifier/lon"
BATTERIES_INSIDE_PARAMETER: Final[str] = "/temperature-notifier/is-inside"

# Open-Meteo request settings.
FORECAST_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS: Final[int] = 10
TEMPERATURE_UNIT: Final[str] = "fahrenheit"
FORECAST_TIMEZONE: Final[str] = "auto"

# Persisted battery-state values.
STATE_INSIDE: Final[str] = "true"
STATE_OUTSIDE: Final[str] = "false"
