import contextlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import Settings, get_settings
from .neis_client import NeisClient, NeisError, NeisTimeout
from .schemas import MealResult, SchoolSearchResult
from .validation import (
    ToolInputError,
    parse_date,
    validate_date_range,
    validate_paging,
    validate_school_identity,
    validate_school_name,
)

logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "대한민국 NEIS 공개 API로 학교를 검색하고 해당 학교의 중식 급식 식단을 조회합니다. "
    "먼저 search_schools 도구로 학교를 찾아 officeCode와 schoolCode를 확보한 뒤 "
    "get_lunch_meals 도구로 날짜별 중식 정보를 조회하세요."
)


@dataclass
class AppContext:
    client: NeisClient


def create_server(settings: Settings | None = None, client: NeisClient | None = None) -> FastMCP:
    resolved = settings or get_settings()

    @contextlib.asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[AppContext]:
        neis = client or NeisClient(resolved)
        try:
            yield AppContext(client=neis)
        finally:
            if client is None:
                await neis.close()

    server = FastMCP(
        name="school-lunch",
        instructions=INSTRUCTIONS,
        host=resolved.mcp_host,
        port=resolved.mcp_port,
        streamable_http_path="/mcp",
        lifespan=lifespan,
    )

    def _client(ctx: Context) -> NeisClient:
        return ctx.request_context.lifespan_context.client

    @server.tool(
        name="search_schools",
        title="학교 검색",
        description=(
            "학교 이름의 일부로 학교를 검색해 후보 학교의 이름, 교육청 정보와 "
            "급식 조회에 필요한 식별 코드(officeCode, schoolCode)를 반환합니다."
        ),
        structured_output=True,
    )
    async def search_schools(
        ctx: Context,
        name: Annotated[str, Field(description="학교 이름의 일부(2자 이상)", min_length=1)],
        page: Annotated[int, Field(ge=1, description="페이지 번호")] = 1,
        size: Annotated[int, Field(ge=1, le=100, description="페이지 크기(최대 100)")] = 20,
    ) -> SchoolSearchResult:
        try:
            cleaned = validate_school_name(name)
            page, size = validate_paging(page, size)
        except ToolInputError as exc:
            raise ToolError(str(exc)) from None

        result = await _call_upstream(_client(ctx).search_schools(cleaned, page, size))
        if not result.items:
            result.message = "검색 결과가 없습니다. 학교 이름을 다시 확인해 주세요."
        return result

    @server.tool(
        name="get_lunch_meals",
        title="중식 급식 조회",
        description=(
            "학교 식별 코드와 조회 기간을 입력하면 NEIS API에서 중식 기준 "
            "날짜별 급식 식단을 조회합니다. 기간은 최대 31일입니다."
        ),
        structured_output=True,
    )
    async def get_lunch_meals(
        ctx: Context,
        office_code: Annotated[
            str, Field(description="시도교육청코드(search_schools 결과)")
        ],
        school_code: Annotated[
            str, Field(description="표준학교코드(search_schools 결과)")
        ],
        from_date: Annotated[str, Field(description="조회 시작일(YYYY-MM-DD)")],
        to_date: Annotated[str, Field(description="조회 종료일(YYYY-MM-DD)")],
    ) -> MealResult:
        try:
            office, school = validate_school_identity(office_code, school_code)
            start = parse_date(from_date, "시작일")
            end = parse_date(to_date, "종료일")
            validate_date_range(start, end)
        except ToolInputError as exc:
            raise ToolError(str(exc)) from None

        meals = await _call_upstream(_client(ctx).get_meals(office, school, start, end))
        if not meals:
            return MealResult(items=[], message="해당 기간에 등록된 중식 급식 정보가 없습니다.")
        return MealResult(items=meals)

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return server


async def _call_upstream[T](awaitable) -> T:
    try:
        return await awaitable
    except NeisTimeout:
        logger.warning("NEIS API timed out")
        raise ToolError("급식 정보 제공 기관의 응답이 지연되어 조회에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None
    except NeisError:
        logger.warning("NEIS API request failed")
        raise ToolError("급식 정보 제공 기관 연동에 실패했습니다. 잠시 후 다시 시도해 주세요.") from None
