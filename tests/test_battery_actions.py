from types import SimpleNamespace

from pytest_bdd import given, parsers, scenarios, then, when

from temperature_notifier import main


scenarios("features/battery_actions.feature")


def _context():
    return {
        "state": None,
        "cold_action_state": "false",
        "minimum": None,
        "maximum": None,
        "messages": [],
        "writes": [],
    }


@given(
    parsers.parse(
        "the acceptable temperature range is {minimum:d} to {maximum:d} degrees Fahrenheit"
    )
)
def acceptable_range(request, minimum, maximum):
    request.node._battery_context = _context()
    request.node._battery_context["config"] = SimpleNamespace(
        temperature=SimpleNamespace(min=minimum, max=maximum)
    )


@given(parsers.parse("batteries are {state}"))
def battery_state(request, state):
    request.node._battery_context["state"] = {
        "inside": "true",
        "outside": "false",
    }[state]


@given(
    parsers.parse(
        "the forecast window has a minimum of {minimum:d} and a maximum of {maximum:d}"
    )
)
def forecast_window(request, minimum, maximum):
    request.node._battery_context["minimum"] = minimum
    request.node._battery_context["maximum"] = maximum


@when("the temperature decision is evaluated")
def evaluate_decision(request, monkeypatch):
    context = request.node._battery_context
    monkeypatch.setattr(
        main,
        "get_value",
        lambda name, **_kwargs: (
            context["state"]
            if name == main.BATTERIES_INSIDE_PARAMETER
            else context["cold_action_state"]
        ),
    )
    monkeypatch.setattr(
        main, "notify_slack", lambda message: context["messages"].append(message)
    )
    monkeypatch.setattr(
        main,
        "set_value",
        lambda name, value: context["writes"].append((name, value)),
    )
    main.decide_action(context["minimum"], context["maximum"], context["config"])


@then(parsers.parse('Slack receives "{message}"'))
def slack_message(request, message):
    if message == "No action needed":
        expected = message
    else:
        expected = f" {main.SLACK_HANDLE} {message}"
    assert request.node._battery_context["messages"] == [expected]


@then(parsers.parse("the battery state is updated to {state}"))
def state_updated(request, state):
    expected = {"inside": "true", "outside": "false"}[state]
    assert request.node._battery_context["writes"] == [
        (main.BATTERIES_INSIDE_PARAMETER, expected)
    ]


@then("the battery state is not updated")
def state_not_updated(request):
    assert not any(
        name == main.BATTERIES_INSIDE_PARAMETER
        for name, _value in request.node._battery_context["writes"]
    )


@then("the cold-weather action state is marked as required")
def cold_weather_state_updated(request):
    assert request.node._battery_context["writes"] == [
        (main.COLD_WEATHER_ACTION_PARAMETER, "true")
    ]
