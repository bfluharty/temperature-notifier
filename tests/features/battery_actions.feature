Feature: Battery action decisions
  The notifier decides whether batteries should move based on their current
  location and the selected forecast window.

  Background:
    Given the acceptable temperature range is 50 to 90 degrees Fahrenheit

  Scenario: Batteries outside and forecast leaves the acceptable range
    Given batteries are outside
    And the forecast window has a minimum of 49 and a maximum of 80
    When the temperature decision is evaluated
    Then Slack receives "Bring in batteries"
    And the battery state is updated to inside

  Scenario: Batteries inside and forecast stays within the acceptable range
    Given batteries are inside
    And the forecast window has a minimum of 50 and a maximum of 90
    When the temperature decision is evaluated
    Then Slack receives "Take out batteries"
    And the battery state is updated to outside

  Scenario: Batteries outside and forecast stays within the acceptable range
    Given batteries are outside
    And the forecast window has a minimum of 50 and a maximum of 90
    When the temperature decision is evaluated
    Then Slack receives "No action needed"
    And the battery state is not updated

  Scenario: Batteries inside and forecast leaves the acceptable range
    Given batteries are inside
    And the forecast window has a minimum of 49 and a maximum of 91
    When the temperature decision is evaluated
    Then Slack receives "No action needed"
    And the battery state is not updated

  Scenario: Cold forecast triggers the fluids and paint reminder
    Given batteries are inside
    And the forecast window has a minimum of 35 and a maximum of 40
    When the temperature decision is evaluated
    Then Slack receives "Bring in fluids and paint"
    And the battery state is not updated
    And the cold-weather action state is marked as required
