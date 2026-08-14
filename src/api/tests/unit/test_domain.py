from datetime import date

import pytest

from app.main_errors import ApiError
from app.neis_client import parse_dishes, to_neis_date
from app.routers.meals import validate_date_range


@pytest.mark.unit
def test_date_and_dish_normalization():
    assert to_neis_date(date(2026, 8, 14)) == "20260814"
    assert parse_dishes("기장밥(5.6.)<br/>미역국 1.2.5.6.13.<br>김치") == [
        "기장밥",
        "미역국",
        "김치",
    ]


@pytest.mark.unit
def test_date_range_uses_inclusive_31_days():
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31))
    with pytest.raises(ApiError, match="31일"):
        validate_date_range(date(2026, 1, 1), date(2026, 2, 1))
    with pytest.raises(ApiError, match="종료일"):
        validate_date_range(date(2026, 1, 2), date(2026, 1, 1))

