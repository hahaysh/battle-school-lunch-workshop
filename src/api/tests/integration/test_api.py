import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("NEIS_API_KEY", "test-secret-value")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.mark.integration
@respx.mock
def test_school_search_and_empty_results(client):
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "schoolInfo": [
                    {
                        "head": [
                            {"list_total_count": 1},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                        ]
                    },
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
            },
        )
    )
    response = client.get("/api/schools", params={"name": "배틀"})
    assert response.status_code == 200
    assert response.json()["items"][0]["schoolName"] == "배틀초등학교"
    assert response.json()["totalCount"] == 1


@pytest.mark.integration
@respx.mock
def test_meals_are_normalized_sorted_and_info_200_is_empty(client):
    route = respx.get("https://open.neis.go.kr/hub/mealServiceDietInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "mealServiceDietInfo": [
                    {
                        "head": [
                            {"list_total_count": 2},
                            {"RESULT": {"CODE": "INFO-000"}},
                        ]
                    },
                    {
                        "row": [
                            {
                                "MLSV_YMD": "20260818",
                                "MMEAL_SC_NM": "중식",
                                "DDISH_NM": "밥(1.2.)<br/>국 5.6.",
                                "CAL_INFO": "800 Kcal",
                                "ORPLC_INFO": "쌀 : 국내산",
                            },
                            {
                                "MLSV_YMD": "20260817",
                                "MMEAL_SC_NM": "중식",
                                "DDISH_NM": "비빔밥",
                                "CAL_INFO": "700 Kcal",
                                "ORPLC_INFO": "",
                            },
                        ]
                    },
                ]
            },
        )
    )
    response = client.get(
        "/api/meals",
        params={
            "officeCode": "J10",
            "schoolCode": "7530575",
            "fromDate": "2026-08-17",
            "toDate": "2026-08-18",
        },
    )
    assert response.status_code == 200
    assert [item["date"] for item in response.json()["items"]] == [
        "2026-08-17",
        "2026-08-18",
    ]
    assert response.json()["items"][1]["dishes"] == ["밥", "국"]
    assert route.calls[0].request.url.params["MMEAL_SC_CODE"] == "2"

    route.mock(return_value=httpx.Response(200, json={"RESULT": {"CODE": "INFO-200"}}))
    assert client.get(
        "/api/meals",
        params={
            "officeCode": "J10",
            "schoolCode": "1",
            "fromDate": "2026-08-17",
            "toDate": "2026-08-17",
        },
    ).json() == {"items": []}


@pytest.mark.integration
def test_validation_errors(client):
    assert client.get("/api/schools", params={"name": "가"}).status_code == 400
    invalid_school = client.get(
        "/api/meals",
        params={
            "officeCode": "invalid-office",
            "schoolCode": "not-a-code",
            "fromDate": "2026-08-17",
            "toDate": "2026-08-17",
        },
    )
    assert invalid_school.status_code == 400
    assert invalid_school.json()["error"]["code"] == "INVALID_SCHOOL"
    response = client.get(
        "/api/meals",
        params={
            "officeCode": "J10",
            "schoolCode": "1",
            "fromDate": "2026-08-31",
            "toDate": "2026-08-01",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"


@pytest.mark.integration
@respx.mock
def test_upstream_error_is_safe(client):
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(500, text="test-secret-value")
    )
    response = client.get("/api/schools", params={"name": "배틀"})
    assert response.status_code == 502
    assert "test-secret-value" not in response.text


@pytest.mark.integration
@respx.mock
def test_upstream_timeout_maps_to_504(client):
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        side_effect=httpx.ReadTimeout("timed out")
    )
    response = client.get("/api/schools", params={"name": "배틀"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
