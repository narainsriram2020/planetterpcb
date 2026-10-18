"""Saved conversations in Supabase Postgres, written through PostgREST with the secret key.

Only the backend writes messages (users can read, rename, and delete their own
chats via row-level security), so stored answers are exactly what TerpGuide said.
Tables are created by backend/supabase/schema.sql.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from planetterp_mcp import config  # noqa: F401 - loads .env before the getenv calls below

logger = logging.getLogger(__name__)

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/") or None
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") or None
TITLE_MAX_CHARS = 80

_client: httpx.AsyncClient | None = None


class ChatStoreError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=f"{SUPABASE_URL}/rest/v1",
            headers={"apikey": SUPABASE_SECRET_KEY, "Content-Type": "application/json"},
            timeout=10,
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        resp = await _http().request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise ChatStoreError(f"Supabase request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise ChatStoreError(f"Supabase returned HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.content else None


def make_title(prompt: str) -> str:
    title = " ".join(prompt.split())
    return title if len(title) <= TITLE_MAX_CHARS else title[: TITLE_MAX_CHARS - 1].rstrip() + "…"


async def create_conversation(user_id: str, title: str) -> str:
    rows = await _request(
        "POST",
        "/conversations",
        json={"user_id": user_id, "title": title},
        headers={"Prefer": "return=representation"},
    )
    return rows[0]["id"]


async def load_history(conversation_id: str, user_id: str, limit: int) -> list[dict[str, str]] | None:
    """The last `limit` messages (oldest first), or None if the conversation isn't this user's."""
    owned = await _request(
        "GET",
        "/conversations",
        params={"id": f"eq.{conversation_id}", "user_id": f"eq.{user_id}", "select": "id"},
    )
    if not owned:
        return None
    rows = await _request(
        "GET",
        "/messages",
        params={
            "conversation_id": f"eq.{conversation_id}",
            "status": "eq.done",
            "select": "role,text",
            "order": "id.desc",
            "limit": str(limit),
        },
    )
    return list(reversed(rows))


async def save_turn(
    conversation_id: str,
    user_id: str,
    prompt: str,
    reply: str,
    steps: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    status: str,
) -> None:
    base = {"conversation_id": conversation_id, "user_id": user_id}
    # PostgREST bulk inserts require every row to have the same keys.
    await _request(
        "POST",
        "/messages",
        json=[
            {**base, "role": "user", "text": prompt, "steps": [], "cards": [], "status": "done"},
            {**base, "role": "bot", "text": reply, "steps": steps, "cards": cards, "status": status},
        ],
        headers={"Prefer": "return=minimal"},
    )


async def delete_user(user_id: str) -> None:
    """Delete the auth user; their conversations and messages go with it (ON DELETE CASCADE)."""
    try:
        resp = await _http().delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {SUPABASE_SECRET_KEY}"},
        )
    except httpx.HTTPError as exc:
        raise ChatStoreError(f"Supabase request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise ChatStoreError(f"Supabase returned HTTP {resp.status_code}: {resp.text[:300]}")


async def ping() -> bool:
    """A tiny query that also counts as activity, so a free-tier project doesn't pause."""
    try:
        await _request("GET", "/conversations", params={"select": "id", "limit": "1"})
        return True
    except ChatStoreError as exc:
        logger.warning("Chat store unavailable: %s", exc)
        return False
