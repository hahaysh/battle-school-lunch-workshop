import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import Settings
from .schemas import Meal, SchoolInput


class McpLunchClient:
    """Small MCP client; the agent never calls NEIS directly."""

    def __init__(self, settings: Settings):
        self.url = settings.mcp_url

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        async with streamablehttp_client(self.url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def get_meals(self, school: SchoolInput, day: date) -> list[Meal]:
        async with self._session() as session:
            result = await session.call_tool(
                "get_lunch_meals",
                arguments={
                    "office_code": school.officeCode,
                    "school_code": school.schoolCode,
                    "from_date": day.isoformat(),
                    "to_date": day.isoformat(),
                },
            )
        structured: Any = getattr(result, "structuredContent", None)
        if structured is None:
            for item in getattr(result, "content", []):
                raw = getattr(item, "text", "")
                try:
                    structured = json.loads(raw)
                    break
                except (TypeError, ValueError):
                    continue
        items = structured.get("items", []) if isinstance(structured, dict) else []
        return [Meal.model_validate(item) for item in items]
