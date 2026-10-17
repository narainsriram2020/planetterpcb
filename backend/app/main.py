"""FastAPI app: the TerpAdvisor chat endpoint plus the PlanetTerp MCP server mounted at /mcp."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from planetterp_mcp import mcp as planetterp_server
from planetterp_mcp import planetterp_api, vector_store

from . import agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12

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
    processing_time: str


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "PlanetTerp Chatbot API", "chat": "POST /chat", "mcp": "/mcp/"}


@app.get("/health")
async def health() -> dict[str, Any]:
    tools = await planetterp_server.list_tools()
    return {
        "status": "ok",
        "gemini_configured": bool(agent.GEMINI_API_KEY),
        "gemini_model": agent.GEMINI_MODEL,
        "vector_store": vector_store.describe_backend(),
        "vector_store_ready": await vector_store.is_ready(),
        "mcp_tools": [tool.name for tool in tools],
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    start = time.perf_counter()
    history = [m.model_dump() for m in req.history[-MAX_HISTORY_MESSAGES:]]
    try:
        result = await agent.answer(prompt, history)
    except agent.AgentUnavailableError as exc:
        logger.warning("Agent unavailable, using fallback: %s", exc)
        try:
            result = await agent.fallback_answer(prompt)
        except Exception:
            logger.exception("Fallback failed")
            raise HTTPException(status_code=503, detail="TerpAdvisor is temporarily unavailable.")
    except Exception:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="Something went wrong answering that.")

    elapsed = time.perf_counter() - start
    logger.info(
        "chat answered in %.2fs with tools %s", elapsed, [call.name for call in result.tool_calls]
    )
    return ChatResponse(
        reply=result.text,
        tools_used=[ToolCallOut(**vars(call)) for call in result.tool_calls],
        processing_time=f"{elapsed:.2f}s",
    )
