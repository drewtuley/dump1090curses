# features/steps/steps_api.py
from behave import given, when, then
import requests
import json


@given("the API base URL is provided")
def step_base_url(context):
    # context.base_url is set in environment.before_all
    assert hasattr(context, "base_url") and context.base_url, "base_url not set"


@when('I request "{path}"')
def step_request_path(context, path):
    url = context.base_url.rstrip("/") + path
    try:
        resp = requests.get(url, timeout=10)
    except Exception as e:
        # re-raise with helpful info
        raise AssertionError(f"Error requesting {url}: {e}")
    context.response = resp
    context.response_text = resp.text


@then("the response status code should be {status:d}")
def step_check_status(context, status):
    actual = context.response.status_code
    if actual != status:
        raise AssertionError(
            f"Expected status {status} but got {actual}. Body:\n{context.response_text}"
        )
    # pass


@then('the response content type should be "{ctype}" if {expect_json}')
def step_check_content_type_if(context, ctype, expect_json):
    expect_json = expect_json.strip().lower() in ("yes", "true", "y", "1")
    if not expect_json:
        return
    content_type = context.response.headers.get("Content-Type", "")
    if ctype not in content_type:
        raise AssertionError(
            f"Expected Content-Type containing '{ctype}', got: '{content_type}'. Body:\n{context.response_text}"
        )


@then("the JSON body should be parseable if {expect_json}")
def step_json_parseable(context, expect_json):
    expect_json = expect_json.strip().lower() in ("yes", "true", "y", "1")
    if not expect_json:
        return
    try:
        context.json = context.response.json()
    except Exception as e:
        raise AssertionError(
            f"Response is not valid JSON: {e}\nBody:\n{context.response_text}"
        )


@then("the JSON body should equal:")
def step_json_equals(context):
    """
    Compares the response JSON to the JSON provided in the feature docstring.
    Uses exact equality (parsed JSON -> Python dict/list comparison).
    """
    # ensure we have a response and it was parsed earlier
    try:
        actual = context.response.json()
    except Exception as e:
        raise AssertionError(
            f"Response is not valid JSON: {e}\nBody:\n{context.response_text}"
        )

    # The feature provides the expected JSON in the step's text block
    expected_text = context.text
    try:
        expected = json.loads(expected_text)
    except Exception as e:
        raise AssertionError(
            f"Expected JSON in feature is invalid: {e}\nFeature text:\n{expected_text}"
        )

    if actual != expected:
        # helpful diff output
        raise AssertionError(
            "JSON body did not match expected value.\n\nExpected:\n{}\n\nActual:\n{}\n".format(
                json.dumps(expected, indent=2, sort_keys=True),
                json.dumps(actual, indent=2, sort_keys=True),
            )
        )
