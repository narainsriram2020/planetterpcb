"""FastAPI app: the TerpGuide chat endpoint plus the PlanetTerp MCP server mounted at /mcp."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from planetterp_mcp import mcp as planetterp_server
from planetterp_mcp import planetterp_api, vector_store

from . import agent, auth, chat_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12
# Per-client chat limit so a public deployment can't drain the Gemini quota.
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "15"))  # requests per window; 0 disables
CHAT_RATE_WINDOW_SECONDS = 600
# Opening questions (no history) are cached so popular ones, like the suggestion
# buttons, don't spend Gemini's free-tier quota on every click.
ANSWER_CACHE_TTL_SECONDS = 6 * 60 * 60
ANSWER_CACHE_MAX_ENTRIES = 500

_recent_requests: dict[str, deque[float]] = defaultdict(deque)
_answer_cache: dict[str, tuple[float, list[dict[str, Any]], agent.AgentReply]] = {}
# Strong references to in-flight chat turns; asyncio only keeps weak ones.
_running_turns: set[asyncio.Task[None]] = set()

mcp_http_app = planetterp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Load the embedding model and check Qdrant in the background so startup stays fast.
    warmup = asyncio.create_task(vector_store.is_ready())
    async with planetterp_server.session_manager.run():
        logger.info(
            "TerpGuide ready (model=%s, vectors=%s, auth required=%s, chat history=%s)",
            agent.GEMINI_MODEL,
            vector_store.describe_backend(),
            auth.REQUIRE_AUTH,
            chat_store.is_configured(),
        )
        yield
    warmup.cancel()
    await planetterp_api.close()
    await chat_store.close()


app = FastAPI(title="TerpGuide", lifespan=lifespan)
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
    # Signed-in users continue a saved conversation by id (history is loaded server-side).
    conversation_id: str | None = None
    # Only used for anonymous requests when sign-in isn't required.
    history: list[HistoryMessage] = []


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]
    ok: bool


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[ToolCallOut]
    cards: list[dict[str, Any]]
    conversation_id: str | None
    processing_time: str


class ChatUnavailableError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "TerpGuide API",
        "chat": "POST /chat",
        "chat_stream": "POST /chat/stream (NDJSON events)",
        "mcp": "/mcp/",
    }


@app.get("/health")
async def health(deep: bool = False) -> dict[str, Any]:
    """`?deep=true` re-checks Qdrant and Supabase, which also counts as activity for free tiers."""
    tools = await planetterp_server.list_tools()
    result: dict[str, Any] = {
        "status": "ok",
        "gemini_configured": bool(agent.GEMINI_API_KEY),
        "gemini_model": agent.GEMINI_MODEL,
        "vector_store": vector_store.describe_backend(),
        "vector_store_ready": await vector_store.is_ready(refresh=deep),
        "auth_required": auth.REQUIRE_AUTH,
        "chat_history_configured": chat_store.is_configured(),
        "mcp_tools": [tool.name for tool in tools],
    }
    if deep and chat_store.is_configured():
        result["chat_history_reachable"] = await chat_store.ping()
    return result


def _client_id(request: Request) -> str:
    # Behind a proxy (Render, Cloud Run) the rightmost X-Forwarded-For entry is
    # the one the proxy itself added, so clients can't spoof it.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str) -> None:
    if CHAT_RATE_LIMIT <= 0:
        return
    now = time.monotonic()
    if len(_recent_requests) > 10_000:  # drop idle clients so memory stays bounded
        for stale in [k for k, v in _recent_requests.items() if not v or now - v[-1] > CHAT_RATE_WINDOW_SECONDS]:
            del _recent_requests[stale]
    hits = _recent_requests[key]
    while hits and now - hits[0] > CHAT_RATE_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= CHAT_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="You're asking faster than TerpGuide can keep up. Give it a few minutes and try again.",
        )
    hits.append(now)


@dataclass
class Turn:
    prompt: str
    history: list[dict[str, str]]
    user: auth.User | None
    conversation_id: str | None = None
    new_conversation: dict[str, Any] | None = None  # emitted first when a chat is created


async def _prepare(req: ChatRequest, request: Request) -> Turn:
    """Authenticate, rate-limit, and resolve the conversation (creating one if needed)."""
    user = await auth.current_user(request)
    _check_rate_limit(f"user:{user.id}" if user else _client_id(request))
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    if not (user and chat_store.is_configured()):
        return Turn(prompt, [m.model_dump() for m in req.history[-MAX_HISTORY_MESSAGES:]], user)

    try:
        if req.conversation_id:
            history = await chat_store.load_history(req.conversation_id, user.id, MAX_HISTORY_MESSAGES)
            if history is None:
                raise HTTPException(status_code=404, detail="That chat doesn't exist or isn't yours.")
            return Turn(prompt, history, user, req.conversation_id)
        title = chat_store.make_title(prompt)
        conversation_id = await chat_store.create_conversation(user.id, title)
    except chat_store.ChatStoreError as exc:
        logger.exception("Chat history unavailable")
        raise HTTPException(status_code=503, detail="Couldn't load your chat history. Try again in a moment.") from exc
    return Turn(prompt, [], user, conversation_id, {"type": "conversation", "id": conversation_id, "title": title})


class TurnRecorder:
    """Passes events through while keeping the final steps and cards for saving."""

    def __init__(self, emit: agent.Emit):
        self._emit = emit
        self.steps: dict[int, dict[str, Any]] = {}
        self.cards: dict[str, dict[str, Any]] = {}

    def __call__(self, event: dict[str, Any]) -> None:
        if event["type"] == "tool_start":
            self.steps[event["id"]] = {
                "id": event["id"], "name": event["name"], "arguments": event["arguments"], "status": "running",
            }
        elif event["type"] == "tool_end" and event["id"] in self.steps:
            self.steps[event["id"]]["status"] = "done" if event["ok"] else "failed"
        elif event["type"] == "card":
            self.cards[event["card"]["key"]] = event["card"]
        self._emit(event)


async def _save(turn: Turn, recorder: TurnRecorder, reply: str, status: str) -> None:
    if not (turn.user and turn.conversation_id):
        return
    try:
        await chat_store.save_turn(
            turn.conversation_id, turn.user.id, turn.prompt, reply,
            list(recorder.steps.values()), list(recorder.cards.values()), status,
        )
    except chat_store.ChatStoreError:
        logger.exception("Failed to save chat turn")  # the user still gets their answer


def _cache_key(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.lower()).strip(" ?!.")


async def _run_turn(prompt: str, history: list[dict[str, str]], emit: agent.Emit) -> agent.AgentReply:
    """One chat turn with the search-only fallback. Raises ChatUnavailableError on failure.

    Opening questions are answered from a short-lived cache when possible; a cache
    hit replays the original events (steps, cards) through `emit`.
    """
    key = _cache_key(prompt) if not history else None
    cached = _answer_cache.get(key) if key else None
    if cached and time.monotonic() - cached[0] < ANSWER_CACHE_TTL_SECONDS:
        for event in cached[1]:
            emit(event)
        logger.info("chat answered from cache: %r", key)
        return cached[2]

    events: list[dict[str, Any]] = []

    def record(event: dict[str, Any]) -> None:
        events.append(event)
        emit(event)

    start = time.perf_counter()
    try:
        result = await agent.answer(prompt, history, record)
    except agent.AgentUnavailableError as exc:
        logger.warning("Agent unavailable, using fallback: %s", exc)
        try:
            result = await agent.fallback_answer(prompt, record)
        except Exception as fallback_exc:
            logger.exception("Fallback failed")
            raise ChatUnavailableError(503, "TerpGuide is temporarily unavailable.") from fallback_exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise ChatUnavailableError(500, "Something went wrong answering that.") from exc
    logger.info(
        "chat answered in %.2fs with tools %s",
        time.perf_counter() - start,
        [call.name for call in result.tool_calls],
    )
    if key and not result.degraded:
        _answer_cache[key] = (time.monotonic(), events, result)
        while len(_answer_cache) > ANSWER_CACHE_MAX_ENTRIES:
            _answer_cache.pop(next(iter(_answer_cache)))
    return result


@app.post("/account/delete", status_code=204)
async def delete_account(request: Request) -> None:
    """Delete the signed-in user's account and every saved chat."""
    user = await auth.current_user(request)
    if user is None or not chat_store.is_configured():
        raise HTTPException(status_code=401, detail="Sign in to delete your account.")
    try:
        await chat_store.delete_user(user.id)
    except chat_store.ChatStoreError as exc:
        logger.exception("Account deletion failed")
        raise HTTPException(status_code=503, detail="Couldn't delete your account. Try again in a moment.") from exc
    logger.info("deleted account %s", user.id)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    turn = await _prepare(req, request)
    start = time.perf_counter()
    recorder = TurnRecorder(lambda _: None)
    try:
        result = await _run_turn(turn.prompt, turn.history, recorder)
    except ChatUnavailableError as exc:
        await _save(turn, recorder, str(exc), "error")
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    await _save(turn, recorder, result.text, "done")
    return ChatResponse(
        reply=result.text,
        tools_used=[ToolCallOut(**vars(call)) for call in result.tool_calls],
        cards=list(recorder.cards.values()),
        conversation_id=turn.conversation_id,
        processing_time=f"{time.perf_counter() - start:.2f}s",
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    """Stream a chat turn as newline-delimited JSON events:

    conversation (a new saved chat was created), tool_start / tool_end (agent
    progress), card (data to display), answer (final text), error, and done.
    """
    turn = await _prepare(req, request)
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    start = time.perf_counter()

    async def run() -> None:
        # The agent runs in its own task so it fully owns its MCP session; the
        # response just drains the queue.
        recorder = TurnRecorder(queue.put_nowait)
        reply, status = "", "done"
        try:
            if turn.new_conversation:
                queue.put_nowait(turn.new_conversation)
            result = await _run_turn(turn.prompt, turn.history, recorder)
            reply = result.text
            queue.put_nowait({"type": "answer", "text": reply})
        except ChatUnavailableError as exc:
            reply, status = str(exc), "error"
            queue.put_nowait({"type": "error", "message": reply})
        finally:
            await _save(turn, recorder, reply, status)
            queue.put_nowait({"type": "done", "processing_time": f"{time.perf_counter() - start:.2f}s"})
            queue.put_nowait(None)

    async def events() -> AsyncIterator[str]:
        task = asyncio.create_task(run())
        _running_turns.add(task)
        task.add_done_callback(_running_turns.discard)
        try:
            while (event := await queue.get()) is not None:
                yield json.dumps(event) + "\n"
        finally:
            # If the client leaves mid-answer, a saved chat still finishes and is
            # stored (it shows up in their history); unsaved turns are abandoned.
            if not turn.conversation_id:
                task.cancel()

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
