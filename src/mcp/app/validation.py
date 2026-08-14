import re
from datetime import date

MAX_RANGE_DAYS = 31
MIN_NAME_LENGTH = 2
MAX_PAGE_SIZE = 100

_OFFICE_CODE_RE = re.compile(r"[A-Za-z0-9]{2,4}")


class ToolInputError(ValueError):
    """A user-facing validation error that never contains sensitive data."""


def validate_school_name(name: str) -> str:
    cleaned = (name or "").strip()
    if len(cleaned) < MIN_NAME_LENGTH:
        raise ToolInputError("학교 이름은 2자 이상 입력해야 합니다.")
    return cleaned


def validate_paging(page: int, size: int) -> tuple[int, int]:
    if page < 1:
        raise ToolInputError("페이지 번호는 1 이상이어야 합니다.")
    if not 1 <= size <= MAX_PAGE_SIZE:
        raise ToolInputError("페이지 크기는 1 이상 100 이하여야 합니다.")
    return page, size


def validate_school_identity(office_code: str, school_code: str) -> tuple[str, str]:
    office = (office_code or "").strip()
    school = (school_code or "").strip()
    if not _OFFICE_CODE_RE.fullmatch(office) or not school.isdigit():
        raise ToolInputError(
            "학교 정보를 확인할 수 없습니다. search_schools 도구로 학교를 먼저 검색해 주세요."
        )
    return office, school


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_date(value: str, label: str) -> date:
    text = (value or "").strip()
    if not _DATE_RE.fullmatch(text):
        raise ToolInputError(f"{label}은(는) YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ToolInputError(f"{label}은(는) 존재하지 않는 날짜입니다.") from exc


def validate_date_range(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise ToolInputError("종료일은 시작일 이후여야 합니다.")
    if (to_date - from_date).days + 1 > MAX_RANGE_DAYS:
        raise ToolInputError("조회 기간은 시작일과 종료일을 포함해 최대 31일입니다.")
