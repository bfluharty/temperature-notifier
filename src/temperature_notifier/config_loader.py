"""Load and validate the notifier's packaged TOML configuration."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when the notifier configuration is missing or invalid."""


@dataclass(frozen=True)
class Temperature:
    """Inclusive acceptable temperature range in Fahrenheit."""

    min: int
    max: int

    def __post_init__(self) -> None:
        if self.min > self.max:
            raise ConfigurationError("temperature.min must not exceed temperature.max")


@dataclass(frozen=True)
class Config:
    """Validated application configuration."""

    forecast_length: int
    temperature: Temperature

    def __post_init__(self) -> None:
        if self.forecast_length < 1:
            raise ConfigurationError("forecast_length must be at least 1")


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")


def _as_integer(value: Any, field_name: str) -> int:
    """Validate that a TOML value is an integer, excluding booleans."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigurationError(f"{field_name} must be an integer")
    return value


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """Load and validate a configuration file, defaulting to packaged config."""
    config_path = Path(path)
    try:
        values = tomllib.loads(config_path.read_text(encoding="utf-8"))
        temperature = values["temperature"]
        if not isinstance(temperature, dict):
            raise ConfigurationError("temperature must be a table")

        return Config(
            forecast_length=_as_integer(values["forecast_length"], "forecast_length"),
            temperature=Temperature(
                min=_as_integer(temperature["min"], "temperature.min"),
                max=_as_integer(temperature["max"], "temperature.max"),
            ),
        )
    except ConfigurationError:
        raise
    except (KeyError, OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"Invalid configuration in {config_path}") from error
