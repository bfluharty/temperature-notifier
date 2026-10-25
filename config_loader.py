import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Temperature:
    min: int
    max: int


@dataclass(frozen=True)
class Config:
    forecast_length: int
    temperature: Temperature


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.toml")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """Load and validate the configuration packaged alongside the handler."""
    with open(path, "rb") as f:
        values = tomllib.load(f)

    try:
        temperature = values["temperature"]
        config = Config(
            forecast_length=int(values["forecast_length"]),
            temperature=Temperature(
                min=int(temperature["min"]),
                max=int(temperature["max"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid configuration in {path}") from error

    if config.forecast_length < 1 or config.temperature.min > config.temperature.max:
        raise ValueError(f"Invalid configuration in {path}")
    return config
