"""TerpGuide: a Gemini agent that answers questions by calling the PlanetTerp MCP tools.

The agent is an MCP client. By default it talks to the in-process server over
an in-memory transport; set MCP_SERVER_URL to use a remote server over
streamable HTTP instead. Each turn, Gemini sees the tool schemas from
`list_tools`, decides which tools to call, and gets the results back until it
can answer (bounded by MAX_TOOL_ROUNDS).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.memory import create_connected_server_and_client_session

from planetterp_mcp import config  # noqa: F401 - loads .env before the getenv calls below
from planetterp_mcp import mcp as planetterp_server

from .cards import card_from_tool

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest"
# Gemini 3 thinks at "high" by default, which roughly triples latency for little
# gain on lookup-style questions. Set to "" for models without thinking levels.
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL") or None
MAX_TOOL_ROUNDS = 6
MAX_GEMINI_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 503}

SYSTEM_PROMPT = """You are TerpGuide, a friendly assistant for University of Maryland students, \
backed by PlanetTerp data on courses, professors, and grades.

How to work:
- For any factual question about courses, professors, GPAs, ratings, or reviews, call the \
tools first. Never invent course ids, GPAs, ratings, names, or review content.
- Only recommend courses and professors that appear in tool results. If the tools find \
nothing that fits, say so plainly; don't fill the gap with courses from memory.
- "Who should I take for X?": call get_grade_distribution for X, then get_professor for \
the 2-3 most relevant recent professors, and weigh GPA, rating, and what reviews say.
- Questions about teaching style ("chill", "clear", "tough grader") need get_professor \
ratings and reviews, not just GPAs.
- "Easy / interesting classes about Y": use search_courses, then compare average GPAs.
- If a tool errors or returns nothing useful, say so and suggest planetterp.com.
- Small talk needs no tools: reply briefly and mention what you can help with.

Style:
- Sound like a helpful UMD upperclassman: casual, direct, no filler openers.
- The app shows the data you fetched as cards under your answer (grade charts, professor \
ratings, course details), so lead with the recommendation and the few numbers that justify it.
- Keep answers under about 150 words. You may use **bold** for course ids and professor \
names and short "-" lists. No headings or tables.
- Give GPAs to two decimals and ratings out of 5."""


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    ok: bool


@dataclass
class AgentReply:
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


class AgentUnavailableError(RuntimeError):
    """Gemini could not produce a reply (missing key, quota, outage)."""


_gemini_client: genai.Client | None = None


def _get_gemini() -> genai.Client:
    global _gemini_client
    if not GEMINI_API_KEY:
        raise AgentUnavailableError("GEMINI_API_KEY is not set.")
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


@asynccontextmanager
async def open_mcp_session() -> AsyncIterator[ClientSession]:
    try:
        if MCP_SERVER_URL:
            async with streamable_http_client(MCP_SERVER_URL) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        else:
            async with create_connected_server_and_client_session(planetterp_server) as session:
                yield session
    except BaseExceptionGroup as group:
        # The MCP transports run in anyio task groups, which wrap errors raised in
        # the `async with` body; unwrap so callers can catch e.g. AgentUnavailableError.
        error: BaseException = group
        while isinstance(error, BaseExceptionGroup) and len(error.exceptions) == 1:
            error = error.exceptions[0]
        if error is group:
            raise
        raise error from None


def _to_function_declarations(tools: list[Any]) -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name=tool.name,
            description=tool.description or "",
            parameters_json_schema=tool.inputSchema,
        )
        for tool in tools
    ]


def _history_to_contents(history: list[dict[str, str]]) -> list[types.Content]:
    contents = []
    for message in history:
        text = (message.get("text") or "").strip()
        if not text:
            continue
        role = "user" if message.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents


async def _call_tool(session: ClientSession, call: types.FunctionCall) -> tuple[dict[str, Any], bool]:
    arguments = dict(call.args or {})
    try:
        result = await session.call_tool(call.name, arguments)
    except Exception as exc:  # noqa: BLE001 - report transport failures to the model
        logger.warning("MCP tool %s failed: %s", call.name, exc)
        return {"error": f"Tool call failed: {exc}"}, False

    text = "\n".join(block.text for block in result.content if getattr(block, "text", None))
    if result.isError:
        return {"error": text or "Tool returned an error."}, False
    if result.structuredContent is not None:
        return result.structuredContent, True
    try:
        return {"result": json.loads(text)}, True
    except (TypeError, ValueError):
        return {"result": text}, True


async def _generate(contents: list[types.Content], config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    client = _get_gemini()
    delay = 1.5
    for attempt in range(1, MAX_GEMINI_ATTEMPTS + 1):
        start = time.perf_counter()
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=config
            )
            usage = response.usage_metadata
            logger.info(
                "Gemini call %.2fs (prompt=%s, thoughts=%s, output=%s tokens)",
                time.perf_counter() - start,
                usage and usage.prompt_token_count,
                usage and usage.thoughts_token_count,
                usage and usage.candidates_token_count,
            )
            return response
        except genai_errors.APIError as exc:
            if exc.code in RETRYABLE_STATUS_CODES and attempt < MAX_GEMINI_ATTEMPTS:
                logger.warning("Gemini %s (attempt %d); retrying in %.1fs", exc.code, attempt, delay)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise AgentUnavailableError(f"Gemini error {exc.code}: {exc.message}") from exc
    raise AgentUnavailableError("Gemini failed after retries.")


Emit = Callable[[dict[str, Any]], None]


def _ignore(_: dict[str, Any]) -> None:
    pass


async def _call_tool_with_events(
    session: ClientSession, call: types.FunctionCall, call_id: int, emit: Emit
) -> tuple[dict[str, Any], bool]:
    arguments = dict(call.args or {})
    emit({"type": "tool_start", "id": call_id, "name": call.name, "arguments": arguments})
    payload, ok = await _call_tool(session, call)
    emit({"type": "tool_end", "id": call_id, "name": call.name, "ok": ok})
    card = card_from_tool(call.name, arguments, payload, ok)
    if card:
        emit({"type": "card", "card": card})
    return payload, ok


async def answer(
    prompt: str, history: list[dict[str, str]] | None = None, emit: Emit = _ignore
) -> AgentReply:
    """Run one chat turn: let Gemini call MCP tools until it produces a final answer.

    Progress (tool calls starting/finishing, data cards) is reported through `emit`
    so the streaming endpoint can show it live.
    """
    records: list[ToolCallRecord] = []
    contents = _history_to_contents(history or [])
    contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

    async with open_mcp_session() as session:
        tools = (await session.list_tools()).tools
        tool_config = types.Tool(function_declarations=_to_function_declarations(tools))

        for round_number in range(MAX_TOOL_ROUNDS + 1):
            final_round = round_number == MAX_TOOL_ROUNDS
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[tool_config],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                # On the last round, force a text answer from whatever was gathered.
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.NONE
                    )
                ) if final_round else None,
                thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL)
                if GEMINI_THINKING_LEVEL else None,
                temperature=0.4,
            )
            response = await _generate(contents, config)
            calls = response.function_calls or []
            if not calls:
                text = (response.text or "").strip()
                if not text:
                    raise AgentUnavailableError("Gemini returned an empty response.")
                return AgentReply(text=text, tool_calls=records)

            # Keep the model turn intact (it carries thought signatures for Gemini 3).
            contents.append(response.candidates[0].content)
            first_id = len(records)
            results = await asyncio.gather(*(
                _call_tool_with_events(session, call, first_id + i, emit)
                for i, call in enumerate(calls)
            ))
            parts = []
            for call, (payload, ok) in zip(calls, results):
                records.append(ToolCallRecord(name=call.name, arguments=dict(call.args or {}), ok=ok))
                parts.append(types.Part.from_function_response(name=call.name, response=payload))
            contents.append(types.Content(role="user", parts=parts))

    raise AgentUnavailableError("Agent did not produce an answer.")


async def fallback_answer(prompt: str, emit: Emit = _ignore) -> AgentReply:
    """Used when Gemini is unavailable: return raw search matches so the user still gets data."""
    call = types.FunctionCall(name="search_courses", args={"query": prompt, "limit": 5})
    async with open_mcp_session() as session:
        payload, ok = await _call_tool_with_events(session, call, 0, emit)
    matches = payload.get("results", []) if ok else []
    if not matches:
        text = "TerpGuide's AI is temporarily unavailable. Try again in a minute, or search planetterp.com directly."
    else:
        lines = ["TerpGuide's AI is temporarily unavailable, but here are courses matching your question:"]
        for course in matches:
            gpa = course.get("average_gpa")
            gpa_text = f" (avg GPA {gpa:.2f})" if isinstance(gpa, (int, float)) else ""
            lines.append(f"- **{course.get('course_id')}**: {course.get('title') or 'Untitled'}{gpa_text}")
        text = "\n".join(lines)
    return AgentReply(
        text=text,
        tool_calls=[ToolCallRecord(name="search_courses", arguments={"query": prompt}, ok=ok)],
    )
