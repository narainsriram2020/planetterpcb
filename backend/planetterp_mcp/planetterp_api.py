"""Async client for the public PlanetTerp API (https://planetterp.com/api)."""

from __future__ import annotations

import html
import re
import time
from typing import Any

import httpx

BASE_URL = "https://planetterp.com/api/v1"
CACHE_TTL_SECONDS = 60 * 60
CACHE_MAX_ENTRIES = 2000
REQUEST_TIMEOUT_SECONDS = 15

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
}

_COURSE_ID_PATTERN = re.compile(r"\b([A-Za-z]{4})\s*-?\s*(\d{3}[A-Za-z]?)\b")
_TAG_PATTERN = re.compile(r"<[^>]+>")

_client: httpx.AsyncClient | None = None
_cache: dict[tuple, tuple[float, Any]] = {}


class PlanetTerpError(RuntimeError):
    """Raised when PlanetTerp is unreachable or returns an unexpected response."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "planetterp-chatbot"},
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _get(path: str, **params: Any) -> Any:
    """GET a PlanetTerp endpoint, returning None for 404s. Responses are cached."""
    params = {k: v for k, v in params.items() if v is not None}
    key = (path, tuple(sorted(params.items())))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        resp = await _get_client().get(path, params=params)
    except httpx.HTTPError as exc:
        raise PlanetTerpError(f"PlanetTerp request failed: {exc}") from exc

    if resp.status_code == 404:
        data = None
    elif resp.status_code != 200:
        raise PlanetTerpError(f"PlanetTerp returned HTTP {resp.status_code} for {path}")
    else:
        data = resp.json()
        if isinstance(data, dict) and "error" in data:
            data = None

    _cache[key] = (time.monotonic(), data)
    while len(_cache) > CACHE_MAX_ENTRIES:
        _cache.pop(next(iter(_cache)))
    return data


def normalize_course_id(value: str) -> str:
    """'cmsc 330' / 'CMSC-330' -> 'CMSC330'."""
    match = _COURSE_ID_PATTERN.search(value or "")
    if match:
        return (match.group(1) + match.group(2)).upper()
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def clean_text(value: str | None) -> str:
    """Strip the HTML tags PlanetTerp embeds in course descriptions."""
    return html.unescape(_TAG_PATTERN.sub("", value or "")).strip()


def compute_gpa(rows: list[dict[str, Any]]) -> tuple[float | None, int]:
    """Weighted GPA and graded-student count across grade rows (W/Other excluded)."""
    total_points = 0.0
    students = 0
    for row in rows:
        for grade, points in GRADE_POINTS.items():
            count = int(row.get(grade) or 0)
            total_points += count * points
            students += count
    if not students:
        return None, 0
    return round(total_points / students, 2), students


async def get_course(course_id: str) -> dict[str, Any] | None:
    return await _get("/course", name=normalize_course_id(course_id))


async def get_professor(name: str) -> dict[str, Any] | None:
    return await _get("/professor", name=name.strip(), reviews="true")


async def get_grades(course_id: str, professor: str | None = None) -> list[dict[str, Any]]:
    data = await _get("/grades", course=normalize_course_id(course_id), professor=professor)
    return data if isinstance(data, list) else []


async def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """PlanetTerp's name search over courses and professors."""
    data = await _get("/search", query=query.strip(), limit=limit)
    return data if isinstance(data, list) else []
