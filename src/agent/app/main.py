import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# These are the official MAF adapters used by the service contract. The
# deterministic stream below keeps tests independent from a model endpoint.
from agent_framework.ag_ui import AgentFrameworkWorkflow
from agent_framework.devui import DevServer

from .config import get_settings
from .mcp_client import McpLunchClient
from .schemas import AnalysisRequest
from .workflow import run_analysis

settings = get_settings()
AG_UI_WORKFLOW_TYPE = AgentFrameworkWorkflow
DEV_UI_SERVER_TYPE = DevServer


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="급식 배틀 분석 에이전트", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)


def event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agui")
async def agui(request: AnalysisRequest) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        yield event({"type": "RUN_STARTED", "message": "멀티에이전트 분석을 준비하고 있어요…"})
        queue: list[dict] = []

        async def progress(name: str, message: str) -> None:
            queue.append({"type": "STEP_FINISHED", "name": name, "message": message})

        try:
            result = await run_analysis(request, McpLunchClient(settings), progress)
            for item in queue:
                yield event(item)
            yield event({"type": "RUN_FINISHED", "message": "분석이 완료되었습니다.", "result": result.model_dump(mode="json")})
        except ValueError as exc:
            yield event({"type": "RUN_ERROR", "message": str(exc)})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.exception_handler(ValueError)
async def value_error(_: object, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": {"code": "INVALID_ANALYSIS", "message": str(exc)}})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.agent_host, port=settings.agent_port)
