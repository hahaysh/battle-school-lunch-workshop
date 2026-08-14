from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .main_errors import ApiError
from .neis_client import NeisClient, NeisError, NeisTimeout
from .routers import health, meals, schools


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.neis_client = NeisClient(get_settings())
    yield
    await app.state.neis_client.close()


app = FastAPI(title="급식 배틀 API", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(schools.router, prefix="/api")
app.include_router(meals.router, prefix="/api")


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content=error_body(exc.code, exc.message)
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("INVALID_QUERY", "요청 값을 확인해 주세요."),
    )


@app.exception_handler(NeisTimeout)
async def timeout_handler(_: Request, __: NeisTimeout) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content=error_body("UPSTREAM_TIMEOUT", "급식 정보를 불러오지 못했습니다."),
    )


@app.exception_handler(NeisError)
async def upstream_handler(_: Request, __: NeisError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=error_body("UPSTREAM_ERROR", "급식 정보를 불러오지 못했습니다."),
    )
