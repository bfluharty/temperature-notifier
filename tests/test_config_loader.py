import pytest

from temperature_notifier.config_loader import (
    Config,
    ConfigurationError,
    Temperature,
    load_config,
)


def write_config(path, contents):
    path.write_text(contents, encoding="utf-8")
    return path


def test_load_config_returns_validated_immutable_values(tmp_path):
    path = write_config(
        tmp_path / "config.toml",
        "forecast_length = 24\n[temperature]\nmin = 50\nmax = 90\n",
    )

    result = load_config(path)

    assert result == Config(24, Temperature(50, 90))
    with pytest.raises(AttributeError):
        result.forecast_length = 12


def test_load_config_rejects_missing_fields(tmp_path):
    path = write_config(tmp_path / "config.toml", "forecast_length = 24\n")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_config(path)


def test_load_config_rejects_malformed_toml(tmp_path):
    path = write_config(tmp_path / "config.toml", "forecast_length = [")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_config(path)


@pytest.mark.parametrize(
    "contents",
    [
        "forecast_length = 0\n[temperature]\nmin = 50\nmax = 90\n",
        "forecast_length = 24\n[temperature]\nmin = 91\nmax = 90\n",
        "forecast_length = true\n[temperature]\nmin = 50\nmax = 90\n",
    ],
)
def test_load_config_rejects_invalid_values(tmp_path, contents):
    path = write_config(tmp_path / "config.toml", contents)

    with pytest.raises(ConfigurationError):
        load_config(path)


def test_load_config_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_config(tmp_path / "missing.toml")
