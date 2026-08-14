from fastapi import APIRouter

from ..schemas import Health

router = APIRouter()


@router.get("/health", response_model=Health)
async def health() -> Health:
    return Health(status="ok")

