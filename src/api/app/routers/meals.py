import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..main_errors import ApiError
from ..neis_client import NeisClient
from ..schemas import MealList
from .dependencies import get_neis_client

router = APIRouter()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(400, "INVALID_QUERY", "날짜는 YYYY-MM-DD 형식이어야 합니다.") from exc


def validate_date_range(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise ApiError(400, "INVALID_DATE_RANGE", "종료일은 시작일 이후여야 합니다.")
    if (to_date - from_date).days + 1 > 31:
        raise ApiError(400, "DATE_RANGE_TOO_LONG", "조회 기간은 최대 31일입니다.")


@router.get("/meals", response_model=MealList, response_model_by_alias=True)
async def meals(
    office_code: Annotated[str, Query(alias="officeCode", min_length=1)],
    school_code: Annotated[str, Query(alias="schoolCode", min_length=1)],
    from_date_value: Annotated[str, Query(alias="fromDate")],
    to_date_value: Annotated[str, Query(alias="toDate")],
    client: NeisClient = Depends(get_neis_client),
) -> MealList:
    if not re.fullmatch(r"[A-Za-z0-9]{2,4}", office_code) or not school_code.isdigit():
        raise ApiError(
            400,
            "INVALID_SCHOOL",
            "학교 정보를 확인할 수 없습니다. 학교를 다시 선택해 주세요.",
        )
    from_date = parse_date(from_date_value)
    to_date = parse_date(to_date_value)
    validate_date_range(from_date, to_date)
    return MealList(
        items=await client.get_meals(office_code, school_code, from_date, to_date)
    )
