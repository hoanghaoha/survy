import pytest

from survy.errors import ParseError
from survy.utils.functions import parse_id


def test_parse_id_id_multi():
    result = parse_id("Q2/A", "id/multi")
    assert result == {"id": "Q2", "multi": "A"}


@pytest.mark.parametrize(
    "s, fmt, expected",
    [
        ("Q1/1", "id/multi", {"id": "Q1", "multi": "1"}),
        ("Q1.2", "id.multi", {"id": "Q1", "multi": "2"}),
    ],
)
def test_parse_id_various_separators(s, fmt, expected):
    assert parse_id(s, fmt) == expected


def test_parse_id_only_id():
    result = parse_id("Q1", "id")
    assert result == {"id": "Q1"}


def test_parse_id_invalid_format():
    with pytest.raises(ParseError):
        parse_id("invalid", "id_multi")


def test_parse_id_partial_match_should_fail():
    # Should fail because pattern must match entire string
    with pytest.raises(ParseError):
        parse_id("Q1_1_extra", "id_multi")


def test_parse_id_wrong_separator():
    # Format expects "_" but string uses "-"
    with pytest.raises(ParseError):
        parse_id("Q1-1", "id_multi")


def test_parse_id_empty_string():
    with pytest.raises(ParseError):
        parse_id("", "id")


def test_parse_id_no_tokens_in_format():
    # No tokens → exact match required
    result = parse_id("ABC", "ABC")
    assert result == {}


def test_parse_id_special_characters_in_values():
    # Values can contain anything except separators
    result = parse_id("Q$1_&2", "id_multi")
    assert result == {"id": "Q$1", "multi": "&2"}
