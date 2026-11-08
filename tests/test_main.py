import logging
from datetime import UTC
from datetime import datetime as real_datetime
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from temperature_notifier import main


def config(forecast_length=3, minimum=50, maximum=90):
    return SimpleNamespace(
        forecast_length=forecast_length,
        temperature=SimpleNamespace(min=minimum, max=maximum),
    )


def expected_notification(message):
    if message == "No action needed":
        return message
    return f" {main.SLACK_HANDLE} {message}"


def fixed_datetime(value):
    class FixedDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return value

    return FixedDatetime


def test_get_forecast_reads_coordinates_and_requests_hourly_fahrenheit():
    response = Mock()
    response.json.return_value = {"hourly": {"temperature_2m": [55]}}

    with (
        patch.object(
            main,
            "get_value",
            side_effect={
                main.LATITUDE_PARAMETER: "40.7",
                main.LONGITUDE_PARAMETER: "-74.0",
            }.get,
        ) as get_value,
        patch.object(main.requests, "get", return_value=response) as request,
    ):
        result = main.get_forecast()

    assert result == response.json.return_value
    get_value.assert_has_calls(
        [call(main.LATITUDE_PARAMETER), call(main.LONGITUDE_PARAMETER)]
    )
    request.assert_called_once_with(
        main.FORECAST_URL,
        params={
            "latitude": "40.7",
            "longitude": "-74.0",
            "hourly": "temperature_2m",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


def test_notify_slack_posts_message_and_propagates_http_failure():
    response = Mock()
    with (
        patch.object(main, "get_value", return_value="https://slack.example/hook"),
        patch.object(main.requests, "post", return_value=response) as post,
    ):
        main.notify_slack("Bring in batteries")

    post.assert_called_once_with(
        "https://slack.example/hook",
        json={"text": "Bring in batteries"},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


def test_notify_slack_raises_when_slack_rejects_request():
    response = Mock()
    response.raise_for_status.side_effect = main.requests.HTTPError("bad response")
    with (
        patch.object(main, "get_value", return_value="https://slack.example/hook"),
        patch.object(main.requests, "post", return_value=response),
    ):
        with pytest.raises(main.requests.HTTPError, match="bad response"):
            main.notify_slack("No action needed")


@pytest.mark.parametrize(
    (
        "inside",
        "cold_action_state",
        "minimum",
        "maximum",
        "message",
        "new_state",
        "cold_new_state",
    ),
    [
        ("false", "false", 49, 80, "Bring in batteries", "true", None),
        ("false", "false", 50, 90, "No action needed", None, None),
        ("true", "false", 50, 90, "Take out batteries", "false", None),
        ("true", "false", 49, 90, "No action needed", None, None),
        ("true", "false", 35, 40, "Bring in fluids and paint", None, "true"),
        (
            "false",
            "false",
            30,
            80,
            "Bring in batteries; Bring in fluids and paint",
            "true",
            "true",
        ),
        ("true", "true", 35, 40, "No action needed", None, None),
        ("true", "true", 36, 40, "Take out fluids and paint", None, "false"),
    ],
)
def test_decide_action_transitions_only_when_a_boundary_is_crossed(
    inside, cold_action_state, minimum, maximum, message, new_state, cold_new_state
):
    notifications = []
    writes = []
    with (
        patch.object(
            main,
            "get_value",
            side_effect=lambda name, **_kwargs: {
                main.BATTERIES_INSIDE_PARAMETER: inside,
                main.COLD_WEATHER_ACTION_PARAMETER: cold_action_state,
            }[name],
        ),
        patch.object(main, "notify_slack", side_effect=notifications.append),
        patch.object(
            main,
            "set_value",
            side_effect=lambda name, value: writes.append((name, value)),
        ),
    ):
        main.decide_action(minimum, maximum, config())

    assert notifications == [expected_notification(message)]
    expected_writes = []
    if new_state is not None:
        expected_writes.append((main.BATTERIES_INSIDE_PARAMETER, new_state))
    if cold_new_state is not None:
        expected_writes.append((main.COLD_WEATHER_ACTION_PARAMETER, cold_new_state))
    assert writes == expected_writes


def test_decide_action_updates_state_after_successful_notification():
    events = []
    with (
        patch.object(main, "get_value", return_value="false"),
        patch.object(
            main, "notify_slack", side_effect=lambda _: events.append("slack")
        ),
        patch.object(main, "set_value", side_effect=lambda *_: events.append("state")),
    ):
        main.decide_action(49, 80, config())

    assert events == ["slack", "state"]


def test_decide_action_does_not_update_state_when_notification_fails():
    with (
        patch.object(
            main,
            "get_value",
            side_effect=lambda name, **_kwargs: {
                main.BATTERIES_INSIDE_PARAMETER: "false",
                main.COLD_WEATHER_ACTION_PARAMETER: "false",
            }[name],
        ),
        patch.object(
            main, "notify_slack", side_effect=RuntimeError("Slack unavailable")
        ),
        patch.object(main, "set_value") as set_value,
    ):
        with pytest.raises(RuntimeError, match="Slack unavailable"):
            main.decide_action(49, 80, config())

    set_value.assert_not_called()


def test_cold_weather_state_is_not_updated_when_notification_fails():
    with (
        patch.object(
            main,
            "get_value",
            side_effect=lambda name, **_kwargs: {
                main.BATTERIES_INSIDE_PARAMETER: "true",
                main.COLD_WEATHER_ACTION_PARAMETER: "false",
            }[name],
        ),
        patch.object(
            main, "notify_slack", side_effect=RuntimeError("Slack unavailable")
        ),
        patch.object(main, "set_value") as set_value,
        pytest.raises(RuntimeError, match="Slack unavailable"),
    ):
        main.decide_action(35, 40, config())

    set_value.assert_not_called()


def test_main_evaluates_forecast_window_from_current_local_hour(caplog):
    forecast = {
        "utc_offset_seconds": -5 * 60 * 60,
        "hourly": {
            "time": [
                "2026-01-02T06:00",
                "2026-01-02T07:00",
                "2026-01-02T08:00",
                "2026-01-02T09:00",
            ],
            "temperature_2m": [20, 48, 55, 95],
        },
    }
    loaded_config = config(forecast_length=2)
    caplog.set_level(logging.INFO)
    with (
        patch.object(main.config_loader, "load_config", return_value=loaded_config),
        patch.object(main, "get_forecast", return_value=forecast),
        patch.object(main, "decide_action") as decide_action,
        patch.object(
            main, "datetime", fixed_datetime(real_datetime(2026, 1, 2, 12, tzinfo=UTC))
        ),
    ):
        main.main()

    decide_action.assert_called_once_with(48, 55, loaded_config)
    assert "Forecast window (2 hours): minimum 48.0 F, maximum 55.0 F" in caplog.text


def test_main_raises_when_current_forecast_hour_is_missing():
    forecast = {
        "utc_offset_seconds": 0,
        "hourly": {"time": ["2026-01-02T07:00"], "temperature_2m": [55]},
    }
    with (
        patch.object(main.config_loader, "load_config", return_value=config()),
        patch.object(main, "get_forecast", return_value=forecast),
        patch.object(
            main, "datetime", fixed_datetime(real_datetime(2026, 1, 2, 6, tzinfo=UTC))
        ),
        pytest.raises(RuntimeError, match="Current forecast hour"),
    ):
        main.main()


def test_forecast_window_rejects_a_window_with_no_temperatures():
    forecast = {
        "utc_offset_seconds": 0,
        "hourly": {"time": ["2026-01-02T08:00"], "temperature_2m": []},
    }
    with pytest.raises(RuntimeError, match="no temperatures"):
        main._forecast_temperatures(
            forecast,
            forecast_length=1,
            now=real_datetime(2026, 1, 2, 8, tzinfo=UTC),
        )


def test_lambda_handler_runs_workflow_and_returns_success_response():
    with patch.object(main, "main") as run:
        result = main.lambda_handler({"source": "aws.scheduler"}, object())

    run.assert_called_once_with()
    assert result == {
        "statusCode": 200,
        "body": "Temperature notification check completed.",
    }
