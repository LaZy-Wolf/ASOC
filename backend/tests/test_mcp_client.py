"""Schema relaxation and argument coercion.

These exist because of a concrete failure: for "Move ticket 1 to in-progress" the model emitted
`{"ticket_id": "1"}`, Groq validated it against the advertised schema and refused the call. It
reproduced across both API keys and at two temperatures, so retrying was not the fix.
"""

from app.mcp_client import _coerce, _relax_integers

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ticket_id": {"type": "integer"},
        "status": {"type": "string", "enum": ["", "open", "closed"]},
        "limit": {"type": "integer", "default": 20},
    },
    "required": ["ticket_id"],
}


def test_integers_are_widened_to_accept_strings():
    relaxed = _relax_integers(SCHEMA)
    assert relaxed["properties"]["ticket_id"]["type"] == ["integer", "string"]
    assert relaxed["properties"]["limit"]["type"] == ["integer", "string"]


def test_relaxing_leaves_everything_else_alone():
    relaxed = _relax_integers(SCHEMA)
    assert relaxed["properties"]["status"] == SCHEMA["properties"]["status"]
    assert relaxed["required"] == ["ticket_id"]
    assert relaxed["additionalProperties"] is False
    # defaults must survive, or optional parameters become required in effect
    assert relaxed["properties"]["limit"]["default"] == 20


def test_relaxing_does_not_mutate_the_original():
    _relax_integers(SCHEMA)
    assert SCHEMA["properties"]["ticket_id"]["type"] == "integer"


def test_quoted_integers_are_coerced_back():
    assert _coerce({"ticket_id": "1"}, SCHEMA)["ticket_id"] == 1
    assert _coerce({"ticket_id": " 42 "}, SCHEMA)["ticket_id"] == 42


def test_real_integers_pass_through():
    assert _coerce({"ticket_id": 7}, SCHEMA)["ticket_id"] == 7


def test_strings_that_are_not_numbers_are_left_for_the_server_to_reject():
    """Silently dropping or zeroing a bad id would turn a clear error into a wrong write."""
    assert _coerce({"ticket_id": "abc"}, SCHEMA)["ticket_id"] == "abc"


def test_string_fields_are_untouched():
    assert _coerce({"status": "open"}, SCHEMA)["status"] == "open"
