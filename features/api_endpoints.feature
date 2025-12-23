Feature: Basic API sanity checks
  As a developer
  I want to ensure the main endpoints respond correctly

  Background:
    Given the API base URL is provided

  Scenario Outline: endpoint returns expected status and valid JSON (when expected)
    When I request "<path>"
    Then the response status code should be <status>
    And the response content type should be "application/json" if <expect_json> is "yes"
    And the JSON body should be parseable if <expect_json> is "yes"

    Examples:
      | path      | status | expect_json |
      | /health   | 200    | yes         |
      | /places   | 200    | yes         |
      | /pois     | 200    | yes         |


    Scenario: search by ICAO returns expected registration and equip
      When I request "/search?icao_code=402271"
      Then the response status code should be 200
      And the response content type should be "application/json" if "yes"
      And the JSON body should be parseable if "yes"
      And the JSON body should equal:
        """
        {"registration": "G-OBMS", "equip": "C172"}
        """

