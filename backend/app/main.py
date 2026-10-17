"""FastAPI app: the TerpAdvisor chat endpoint plus the PlanetTerp MCP server mounted at /mcp."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from planetterp_mcp import mcp as planetterp_server
from planetterp_mcp import planetterp_api, vector_store

from . import agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12
# Per-client chat limit so a public deployment can't drain the Gemini quota.
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "30"))  # requests per window; 0 disables
CHAT_RATE_WINDOW_SECONDS = 600

_recent_requests: dict[str, deque[float]] = defaultdict(deque)

mcp_http_app = planetterp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Load the embedding model and check Qdrant in the background so startup stays fast.
    warmup = asyncio.create_task(vector_store.is_ready())
    async with planetterp_server.session_manager.run():
        logger.info("TerpAdvisor ready (model=%s, vectors=%s)", agent.GEMINI_MODEL, vector_store.describe_backend())
        yield
    warmup.cancel()
    await planetterp_api.close()


app = FastAPI(title="TerpAdvisor", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGINS", "*").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/mcp", mcp_http_app)


class HistoryMessage(BaseModel):
    role: str  # "user" or "bot"
    text: str


class ChatRequest(BaseModel):
    prompt: str = Field(..., max_length=2000)
    history: list[HistoryMessage] = []


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]
    ok: bool


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[ToolCallOut]
    cards: list[dict[str, Any]]
    processing_time: str


class ChatUnavailableError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "TerpAdvisor API",
        "chat": "POST /chat",
        "chat_stream": "POST /chat/stream (NDJSON events)",
        "mcp": "/mcp/",
    }


@app.get("/health")
async def health(deep: bool = False) -> dict[str, Any]:
    """`?deep=true` re-checks Qdrant, which also counts as activity for free-tier clusters."""
    tools = await planetterp_server.list_tools()
    return {
        "status": "ok",
        "gemini_configured": bool(agent.GEMINI_API_KEY),
        "gemini_model": agent.GEMINI_MODEL,
        "vector_store": vector_store.describe_backend(),
        "vector_store_ready": await vector_store.is_ready(refresh=deep),
        "mcp_tools": [tool.name for tool in tools],
    }


def _client_id(request: Request) -> str:
    # Behind a proxy (Render, Cloud Run) the rightmost X-Forwarded-For entry is
    # the one the proxy itself added, so clients can't spoof it.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    if CHAT_RATE_LIMIT <= 0:
        return
    now = time.monotonic()
    if len(_recent_requests) > 10_000:  # drop idle clients so memory stays bounded
        for key in [k for k, v in _recent_requests.items() if not v or now - v[-1] > CHAT_RATE_WINDOW_SECONDS]:
            del _recent_requests[key]
    hits = _recent_requests[_client_id(request)]
    while hits and now - hits[0] > CHAT_RATE_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= CHAT_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="You're asking faster than TerpAdvisor can keep up. Give it a few minutes and try again.",
        )
    hits.append(now)


def _parse(req: ChatRequest) -> tuple[str, list[dict[str, str]]]:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    return prompt, [m.model_dump() for m in req.history[-MAX_HISTORY_MESSAGES:]]


async def _run_turn(prompt: str, history: list[dict[str, str]], emit: agent.Emit) -> agent.AgentReply:
    """One chat turn with the search-only fallback. Raises ChatUnavailableError on failure."""
    start = time.perf_counter()
    try:
        result = await agent.answer(prompt, history, emit)
    except agent.AgentUnavailableError as exc:
        logger.warning("Agent unavailable, using fallback: %s", exc)
        try:
            result = await agent.fallback_answer(prompt, emit)
        except Exception as fallback_exc:
            logger.exception("Fallback failed")
            raise ChatUnavailableError(503, "TerpAdvisor is temporarily unavailable.") from fallback_exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise ChatUnavailableError(500, "Something went wrong answering that.") from exc
    logger.info(
        "chat answered in %.2fs with tools %s",
        time.perf_counter() - start,
        [call.name for call in result.tool_calls],
    )
    return result


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    _check_rate_limit(request)
    prompt, history = _parse(req)
    start = time.perf_counter()
    cards: dict[str, dict[str, Any]] = {}

    def collect(event: dict[str, Any]) -> None:
        if event["type"] == "card":
            cards[event["card"]["key"]] = event["card"]

    try:
        result = await _run_turn(prompt, history, collect)
    except ChatUnavailableError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return ChatResponse(
        reply=result.text,
        tools_used=[ToolCallOut(**vars(call)) for call in result.tool_calls],
        cards=list(cards.values()),
        processing_time=f"{time.perf_counter() - start:.2f}s",
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    """Stream a chat turn as newline-delimited JSON events:

    tool_start / tool_end (agent progress), card (data to display),
    answer (final text), error, and done.
    """
    _check_rate_limit(request)
    prompt, history = _parse(req)
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    start = time.perf_counter()

    async def run() -> None:
        # The agent runs in its own task so it fully owns its MCP session; the
        # response just drains the queue.
        try:
            result = await _run_turn(prompt, history, queue.put_nowait)
            queue.put_nowait({"type": "answer", "text": result.text})
        except ChatUnavailableError as exc:
            queue.put_nowait({"type": "error", "message": str(exc)})
        finally:
            queue.put_nowait({"type": "done", "processing_time": f"{time.perf_counter() - start:.2f}s"})
            queue.put_nowait(None)

    async def events() -> AsyncIterator[str]:
        task = asyncio.create_task(run())
        try:
            while (event := await queue.get()) is not None:
                yield json.dumps(event) + "\n"
        finally:
            task.cancel()  # client went away mid-answer

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
