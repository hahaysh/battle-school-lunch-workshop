import json

import httpx
import pytest
import respx
from mcp.shared.memory import create_connected_server_and_client_session

from app.config import Settings
from app.neis_client import NeisClient
from app.server import create_server

pytestmark = pytest.mark.integration

BASE_URL = "https://neis.test/hub"
API_KEY = "test-secret-key"

SCHOOL_PAYLOAD = {
    "schoolInfo": [
        {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000"}}]},
        {
            "row": [
                {
                    "ATPT_OFCDC_SC_CODE": "J10",
                    "ATPT_OFCDC_SC_NM": "경기도교육청",
                    "SD_SCHUL_CODE": "7530575",
                    "SCHUL_NM": "배틀초등학교",
                    "SCHUL_KND_SC_NM": "초등학교",
                    "ORG_RDNMA": "경기도 성남시",
                }
            ]
        },
    ]
}

MEAL_PAYLOAD = {
    "mealServiceDietInfo": [
        {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000"}}]},
        {
            "row": [
                {
                    "MLSV_YMD": "20260817",
                    "MMEAL_SC_NM": "중식",
                    "DDISH_NM": "기장밥<br/>미역국 (1.5)",
                    "CAL_INFO": "812.3 Kcal",
                    "ORPLC_INFO": "쌀 : 국내산",
                }
            ]
        },
    ]
}

NO_RESULT_PAYLOAD = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "데이터가 없습니다."}}


def build_settings() -> Settings:
    return Settings(
        neis_api_key=API_KEY,
        neis_base_url=BASE_URL,
        neis_timeout_seconds=1.0,
        neis_max_retries=0,
    )


def make_session():
    settings = build_settings()
    client = NeisClient(
        settings,
        client=httpx.AsyncClient(base_url=BASE_URL, timeout=httpx.Timeout(1.0)),
    )
    return create_connected_server_and_client_session(
        create_server(settings, client)._mcp_server
    )


def structured(result) -> dict:
    assert result.isError is False
    return result.structuredContent


def text_of(result) -> str:
    return " ".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )


async def test_list_tools_exposes_both_tools():
    async with make_session() as session:
        tools = await session.list_tools()
    names = {tool.name for tool in tools.tools}
    assert names == {"search_schools", "get_lunch_meals"}


@respx.mock
async def test_search_schools_returns_candidates():
    route = respx.get(f"{BASE_URL}/schoolInfo").mock(
        return_value=httpx.Response(200, json=SCHOOL_PAYLOAD)
    )
    async with make_session() as session:
        result = await session.call_tool("search_schools", {"name": "배틀"})

    assert route.called
    payload = structured(result)
    assert payload["totalCount"] == 1
    assert payload["items"][0]["schoolCode"] == "7530575"
    assert payload["items"][0]["officeCode"] == "J10"


@respx.mock
async def test_search_schools_without_results_returns_message():
    respx.get(f"{BASE_URL}/schoolInfo").mock(
        return_value=httpx.Response(200, json=NO_RESULT_PAYLOAD)
    )
    async with make_session() as session:
        result = await session.call_tool("search_schools", {"name": "없는학교"})

    payload = structured(result)
    assert payload["items"] == []
    assert payload["totalCount"] == 0
    assert "검색 결과가 없습니다" in payload["message"]


async def test_search_schools_rejects_short_name():
    async with make_session() as session:
        result = await session.call_tool("search_schools", {"name": "배"})

    assert result.isError is True
    assert "2자 이상" in text_of(result)


@respx.mock
async def test_get_lunch_meals_returns_normalized_meals():
    route = respx.get(f"{BASE_URL}/mealServiceDietInfo").mock(
        return_value=httpx.Response(200, json=MEAL_PAYLOAD)
    )
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "7530575",
                "from_date": "2026-08-17",
                "to_date": "2026-08-21",
            },
        )

    assert route.calls.last.request.url.params["MMEAL_SC_CODE"] == "2"
    assert route.calls.last.request.url.params["MLSV_FROM_YMD"] == "20260817"
    payload = structured(result)
    assert payload["items"][0]["dishes"] == ["기장밥", "미역국"]
    assert payload["items"][0]["mealType"] == "중식"


@respx.mock
async def test_get_lunch_meals_without_results_returns_message():
    respx.get(f"{BASE_URL}/mealServiceDietInfo").mock(
        return_value=httpx.Response(200, json=NO_RESULT_PAYLOAD)
    )
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "7530575",
                "from_date": "2026-08-17",
                "to_date": "2026-08-21",
            },
        )

    payload = structured(result)
    assert payload["items"] == []
    assert "급식 정보가 없습니다" in payload["message"]


async def test_get_lunch_meals_rejects_long_range():
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "7530575",
                "from_date": "2026-08-01",
                "to_date": "2026-09-05",
            },
        )

    assert result.isError is True
    assert "최대 31일" in text_of(result)


async def test_get_lunch_meals_rejects_reversed_range():
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "7530575",
                "from_date": "2026-08-10",
                "to_date": "2026-08-01",
            },
        )

    assert result.isError is True
    assert "종료일은 시작일 이후" in text_of(result)


async def test_get_lunch_meals_rejects_invalid_school_code():
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "not-a-code",
                "from_date": "2026-08-17",
                "to_date": "2026-08-21",
            },
        )

    assert result.isError is True
    assert "학교 정보를 확인할 수 없습니다" in text_of(result)


@respx.mock
async def test_upstream_error_is_masked():
    respx.get(f"{BASE_URL}/schoolInfo").mock(
        return_value=httpx.Response(500, json={"detail": API_KEY})
    )
    async with make_session() as session:
        result = await session.call_tool("search_schools", {"name": "배틀"})

    assert result.isError is True
    message = text_of(result)
    assert API_KEY not in message
    assert "연동에 실패" in message


@respx.mock
async def test_upstream_timeout_is_masked():
    respx.get(f"{BASE_URL}/mealServiceDietInfo").mock(
        side_effect=httpx.ReadTimeout("timeout")
    )
    async with make_session() as session:
        result = await session.call_tool(
            "get_lunch_meals",
            {
                "office_code": "J10",
                "school_code": "7530575",
                "from_date": "2026-08-17",
                "to_date": "2026-08-21",
            },
        )

    assert result.isError is True
    message = text_of(result)
    assert API_KEY not in message
    assert "응답이 지연" in message


@respx.mock
async def test_api_key_is_sent_upstream_only():
    respx.get(f"{BASE_URL}/schoolInfo").mock(
        return_value=httpx.Response(200, json=SCHOOL_PAYLOAD)
    )
    async with make_session() as session:
        result = await session.call_tool("search_schools", {"name": "배틀"})

    assert API_KEY not in json.dumps(structured(result), ensure_ascii=False)
