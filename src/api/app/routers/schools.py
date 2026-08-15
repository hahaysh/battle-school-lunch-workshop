import random
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..main_errors import ApiError
from ..neis_client import NeisClient
from ..schemas import SchoolList
from .dependencies import get_neis_client

router = APIRouter()


@router.get("/schools/random", response_model=SchoolList, response_model_by_alias=True)
async def random_schools(
    client: NeisClient = Depends(get_neis_client),
) -> SchoolList:
    """Return a bounded, randomly ordered set for the analysis picker."""
    result = await client.search_schools("학교", 1, 100)
    if len(result.items) <= 10:
        return result
    return SchoolList(items=random.sample(result.items, 10), totalCount=10)


@router.get("/schools", response_model=SchoolList, response_model_by_alias=True)
async def schools(
    name: Annotated[str, Query()],
    page: Annotated[int, Query()] = 1,
    size: Annotated[int, Query()] = 50,
    client: NeisClient = Depends(get_neis_client),
) -> SchoolList:
    query = name.strip()
    if len(query) < 2 or page < 1 or not 1 <= size <= 100:
        raise ApiError(400, "INVALID_QUERY", "검색어는 2자 이상 입력해 주세요.")
    return await client.search_schools(query, page, size)
