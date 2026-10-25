from types import SimpleNamespace

from pytest_bdd import given, parsers, scenarios, then, when

from temperature_notifier import main


scenarios("features/battery_actions.feature")


def _context():
    return {
        "state": None,
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
    monkeypatch.setattr(main, "get_value", lambda _name, **_kwargs: context["state"])
    monkeypatch.setattr(
        main, "notify_slack", lambda message: context["messages"].append(message)
    )
    monkeypatch.setattr(
        main, "set_value", lambda _name, value: context["writes"].append(value)
    )
    main.decide_action(context["minimum"], context["maximum"], context["config"])


@then(parsers.parse('Slack receives "{message}"'))
def slack_message(request, message):
    assert request.node._battery_context["messages"] == [message]


@then(parsers.parse("the battery state is updated to {state}"))
def state_updated(request, state):
    expected = {"inside": "true", "outside": "false"}[state]
    assert request.node._battery_context["writes"] == [expected]


@then("the battery state is not updated")
def state_not_updated(request):
    assert request.node._battery_context["writes"] == []
