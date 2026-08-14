import asyncio
import html
import re
from datetime import date
from typing import Any

import httpx

from .config import Settings
from .schemas import Meal, School, SchoolSearchResult


class NeisError(Exception):
    """A safe upstream error with no response payload or credentials."""


class NeisTimeout(NeisError):
    pass


_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ALLERGY_RE = re.compile(r"\s*\(?(?:\d+\.)*\d+\.?\)?\s*$")


def to_neis_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def parse_dishes(value: str) -> list[str]:
    dishes: list[str] = []
    for raw in _BREAK_RE.split(html.unescape(value or "")):
        dish = _ALLERGY_RE.sub("", raw.strip()).strip()
        if dish:
            dishes.append(dish)
    return dishes


def _result_code(payload: dict[str, Any], resource: str) -> str | None:
    direct = payload.get("RESULT")
    if isinstance(direct, dict):
        return direct.get("CODE")
    groups = payload.get(resource)
    if isinstance(groups, list) and groups:
        for entry in groups[0].get("head", []):
            if isinstance(entry, dict) and isinstance(entry.get("RESULT"), dict):
                return entry["RESULT"].get("CODE")
    return None


def _rows(payload: dict[str, Any], resource: str) -> list[dict[str, Any]]:
    groups = payload.get(resource)
    if not isinstance(groups, list):
        return []
    for group in groups:
        rows = group.get("row")
        if isinstance(rows, list):
            return rows
    return []


def _total(payload: dict[str, Any], resource: str) -> int:
    groups = payload.get(resource)
    if isinstance(groups, list) and groups:
        for entry in groups[0].get("head", []):
            if isinstance(entry, dict) and "list_total_count" in entry:
                try:
                    return int(entry["list_total_count"])
                except (TypeError, ValueError):
                    return 0
    return len(_rows(payload, resource))


def _parse_meal_date(value: Any) -> date | None:
    text = str(value or "")
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    if len(text) == 8 and text.isdigit():
        try:
            return date.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:8]}")
        except ValueError:
            return None
    return None


class NeisClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            base_url=settings.neis_base_url,
            timeout=httpx.Timeout(settings.neis_timeout_seconds),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        safe_params = {"Type": "json", **params}
        if self.settings.neis_api_key:
            safe_params["KEY"] = self.settings.neis_api_key

        for attempt in range(self.settings.neis_max_retries + 1):
            try:
                response = await self.client.get(path, params=safe_params)
                if response.status_code >= 500 and attempt < self.settings.neis_max_retries:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise NeisError("NEIS API returned an invalid response")
                return payload
            except httpx.TimeoutException as exc:
                if attempt == self.settings.neis_max_retries:
                    raise NeisTimeout("NEIS API timed out") from exc
            except (httpx.HTTPError, ValueError) as exc:
                if isinstance(exc, httpx.TransportError) and attempt < self.settings.neis_max_retries:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                raise NeisError("NEIS API request failed") from exc
        raise NeisError("NEIS API request failed")

    @staticmethod
    def _ensure_success(payload: dict[str, Any], resource: str) -> bool:
        code = _result_code(payload, resource)
        if code == "INFO-200":
            return False
        if code and code != "INFO-000":
            raise NeisError("NEIS API rejected the request")
        return True

    async def search_schools(self, name: str, page: int, size: int) -> SchoolSearchResult:
        resource = "schoolInfo"
        payload = await self._get(
            resource,
            {"pIndex": page, "pSize": size, "SCHUL_NM": name},
        )
        if not self._ensure_success(payload, resource):
            return SchoolSearchResult(items=[], totalCount=0)
        items = [
            School(
                officeCode=row.get("ATPT_OFCDC_SC_CODE", ""),
                officeName=row.get("ATPT_OFCDC_SC_NM", ""),
                schoolCode=row.get("SD_SCHUL_CODE", ""),
                schoolName=row.get("SCHUL_NM", ""),
                schoolKind=row.get("SCHUL_KND_SC_NM", ""),
                address=row.get("ORG_RDNMA", ""),
            )
            for row in _rows(payload, resource)
        ]
        return SchoolSearchResult(items=items, totalCount=_total(payload, resource))

    async def get_meals(
        self, office_code: str, school_code: str, from_date: date, to_date: date
    ) -> list[Meal]:
        resource = "mealServiceDietInfo"
        payload = await self._get(
            resource,
            {
                "ATPT_OFCDC_SC_CODE": office_code,
                "SD_SCHUL_CODE": school_code,
                "MMEAL_SC_CODE": "2",
                "MLSV_FROM_YMD": to_neis_date(from_date),
                "MLSV_TO_YMD": to_neis_date(to_date),
            },
        )
        if not self._ensure_success(payload, resource):
            return []
        meals: list[Meal] = []
        for row in _rows(payload, resource):
            meal_date = _parse_meal_date(row.get("MLSV_YMD"))
            if meal_date is None:
                continue
            meals.append(
                Meal(
                    date=meal_date,
                    mealType=row.get("MMEAL_SC_NM", "중식"),
                    dishes=parse_dishes(row.get("DDISH_NM", "")),
                    calorie=row.get("CAL_INFO", ""),
                    origin=row.get("ORPLC_INFO", ""),
                )
            )
        return sorted(meals, key=lambda meal: meal.meal_date)
