from datetime import date

import pytest

from app.neis_client import parse_dishes, to_neis_date
from app.validation import (
    ToolInputError,
    parse_date,
    validate_date_range,
    validate_paging,
    validate_school_identity,
    validate_school_name,
)

pytestmark = pytest.mark.unit


def test_to_neis_date():
    assert to_neis_date(date(2026, 8, 17)) == "20260817"


def test_parse_dishes_strips_breaks_and_allergy_numbers():
    raw = "기장밥<br/>미역국 (1.5.9)<br/>제육볶음 5.6.10.<br/>"
    assert parse_dishes(raw) == ["기장밥", "미역국", "제육볶음"]


def test_parse_dishes_handles_empty():
    assert parse_dishes("") == []


def test_validate_school_name_requires_two_characters():
    assert validate_school_name(" 배틀 ") == "배틀"
    with pytest.raises(ToolInputError):
        validate_school_name("배")


def test_validate_paging_bounds():
    assert validate_paging(1, 20) == (1, 20)
    with pytest.raises(ToolInputError):
        validate_paging(0, 20)
    with pytest.raises(ToolInputError):
        validate_paging(1, 101)


def test_validate_school_identity():
    assert validate_school_identity("J10", "7530575") == ("J10", "7530575")
    with pytest.raises(ToolInputError):
        validate_school_identity("J10", "abc")
    with pytest.raises(ToolInputError):
        validate_school_identity("!!", "7530575")


def test_parse_date_rejects_invalid_format():
    assert parse_date("2026-08-17", "시작일") == date(2026, 8, 17)
    with pytest.raises(ToolInputError):
        parse_date("20260817", "시작일")


def test_validate_date_range():
    validate_date_range(date(2026, 8, 1), date(2026, 8, 31))
    with pytest.raises(ToolInputError):
        validate_date_range(date(2026, 8, 2), date(2026, 8, 1))
    with pytest.raises(ToolInputError):
        validate_date_range(date(2026, 8, 1), date(2026, 9, 1))
