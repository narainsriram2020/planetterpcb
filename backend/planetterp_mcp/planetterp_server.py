"""PlanetTerp FastMCP server definition and helper utilities."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable, Sequence

#from mcp.server.fastmcp import Context, FastMCP
from backend.planetterp_mcp.mcp_stub import MCPServer, ToolResult

from backend.planetterp_core import (
    extract_course_ids,
    get_course,
    get_course_grades,
    get_courses,
    get_professor,
    get_rating_emoji,
)

from .planetterp_models import (
    CourseDetails,
    CourseIdExtraction,
    CourseSummary,
    GradeBreakdown,
    ProfessorProfile,
    ProfessorReview,
)
from .vector_store import ensure_vector_store, semantic_course_search

COURSE_CACHE_TTL_SECONDS = 60 * 60  # 1 hour
_course_cache: list[dict[str, Any]] | None = None
_course_cache_index: dict[str, dict[str, Any]] = {}
_course_cache_timestamp: float = 0.0
_course_cache_lock = asyncio.Lock()

PLANETTERP_MCP_SERVER = MCPServer("PlanetTerp MCP")



async def _run_blocking(func, *args, **kwargs):
    """Run blocking PlanetTerp helper functions without blocking the event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)


async def ensure_course_cache(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Warm and provide the shared course cache."""
    global _course_cache, _course_cache_index, _course_cache_timestamp

    async with _course_cache_lock:
        cache_stale = (time.time() - _course_cache_timestamp) > COURSE_CACHE_TTL_SECONDS
        if force_refresh or _course_cache is None or cache_stale:
            courses = await _run_blocking(get_courses)
            course_index: dict[str, dict[str, Any]] = {}
            for course in courses:
                course_id = course.get("course_id") or course.get("name")
                if not course_id:
                    continue
                course_index[course_id.upper()] = course
            _course_cache = courses
            _course_cache_index = course_index
            _course_cache_timestamp = time.time()

        vector_force_refresh = force_refresh or cache_stale
        try:
            await ensure_vector_store(_course_cache or [], force_rebuild=vector_force_refresh)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  Failed to prepare semantic index: {exc}")

        return _course_cache or []


async def ensure_course_cache_warmed(force_refresh: bool = False) -> int:
    """Public helper to warm the cache; returns number of cached courses."""
    courses = await ensure_course_cache(force_refresh=force_refresh)
    return len(courses)


def _build_course_summary(raw: dict[str, Any], *, score: float | None = None) -> CourseSummary:
    return CourseSummary(
        course_id=raw.get("course_id") or raw.get("name", ""),
        title=raw.get("title"),
        description=raw.get("description"),
        department=raw.get("department"),
        credits=str(raw.get("credits")) if raw.get("credits") is not None else raw.get("credits"),
        score=score,
    )


def _build_professor_profile(raw: dict[str, Any], *, limit_reviews: int | None = 3) -> ProfessorProfile:
    reviews = raw.get("reviews") or []
    normalized_reviews: list[ProfessorReview] = []
    for review in reviews[: limit_reviews or len(reviews)]:
        normalized_reviews.append(
            ProfessorReview(
                created=review.get("created"),
                rating=review.get("rating"),
                difficulty=review.get("difficulty"),
                comment=review.get("review"),
            )
        )

    average_rating = raw.get("average_rating")

    return ProfessorProfile(
        name=raw.get("name") or raw.get("professor", ""),
        average_rating=average_rating,
        rating_emoji=get_rating_emoji(average_rating) if average_rating else None,
        department=raw.get("department"),
        courses=[course for course in raw.get("courses", []) if isinstance(course, str)],
        num_reviews=len(reviews),
        reviews=normalized_reviews,
    )


def _normalize_grade_entry(entry: dict[str, Any]) -> GradeBreakdown:
    normalized = {}
    for key, value in entry.items():
        if key and isinstance(key, str):
            normalized[key.replace(" ", "_")] = value
    return GradeBreakdown.model_validate(normalized)


async def _load_course(course_id: str) -> dict[str, Any] | None:
    await ensure_course_cache()
    cached = _course_cache_index.get(course_id.upper())
    if cached:
        return cached
    return await _run_blocking(get_course, course_id.upper())


async def _load_course_grades(course_id: str) -> list[dict[str, Any]]:
    return await _run_blocking(get_course_grades, course_id.upper())


async def _load_professor(name: str) -> dict[str, Any] | None:
    return await _run_blocking(get_professor, name)


@PLANETTERP_MCP_SERVER.tool(
    name="extract_course_ids",
    description="Find PlanetTerp course identifiers within free-form text.",
    structured_output=True,
)
async def tool_extract_course_ids(text: str) -> CourseIdExtraction:
    matches = extract_course_ids(text or "")
    return CourseIdExtraction(course_ids=matches)


@PLANETTERP_MCP_SERVER.tool(
    name="search_courses",
    description="Search the PlanetTerp catalog by keyword.",
    structured_output=True,
)
async def tool_search_courses(query: str, limit: int = 5) -> Sequence[CourseSummary]:
    if not query or not query.strip():
        return []

    courses = await ensure_course_cache()
    results: list[CourseSummary] = []
    seen: set[str] = set()

    try:
        semantic_hits = await semantic_course_search(query, limit=limit * 2)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Semantic search failed: {exc}")
        semantic_hits = []

    for hit in semantic_hits:
        course_id = str(hit.get("course_id") or "").upper()
        if not course_id or course_id in seen:
            continue
        raw = _course_cache_index.get(course_id)
        if raw:
            results.append(_build_course_summary(raw, score=hit.get("score")))
        else:
            fallback = {
                "course_id": course_id,
                "title": hit.get("title"),
                "description": hit.get("description"),
                "department": hit.get("department"),
                "credits": hit.get("credits"),
            }
            results.append(_build_course_summary(fallback, score=hit.get("score")))
        seen.add(course_id)
        if len(results) >= limit:
            break

    if len(results) < limit:
        query_terms = [term for term in query.lower().split() if len(term) > 2]
        lexical_scored: list[tuple[int, dict[str, Any]]] = []

        for course in courses:
            course_id = course.get("course_id") or course.get("name")
            if not course_id or course_id.upper() in seen:
                continue
            corpus = " ".join(
                filter(
                    None,
                    [
                        course_id,
                        course.get("title") or "",
                        course.get("description") or "",
                    ],
                )
            ).lower()
            score = sum(1 for term in query_terms if term in corpus)
            if score:
                lexical_scored.append((score, course))

        lexical_scored.sort(key=lambda item: item[0], reverse=True)
        for _, course in lexical_scored:
            course_id = course.get("course_id") or course.get("name")
            if not course_id or course_id.upper() in seen:
                continue
            results.append(_build_course_summary(course))
            seen.add(course_id.upper())
            if len(results) >= limit:
                break

    return results


@PLANETTERP_MCP_SERVER.tool(
    name="get_course_details",
    description="Retrieve detailed PlanetTerp data for a specific course.",
    structured_output=True,
)
async def tool_get_course_details(
    course_id: str,
    include_professors: bool = True,
    include_grades: bool = True,
    professor_review_limit: int = 3,
    grade_entry_limit: int = 3,
) -> CourseDetails:
    if not course_id:
        raise ValueError("course_id is required")

    course = await _load_course(course_id)
    if not course:
        raise ValueError(f"Course '{course_id}' not found on PlanetTerp.")

    details = CourseDetails(
        course_id=course.get("course_id") or course.get("name", course_id),
        title=course.get("title"),
        description=course.get("description"),
        credits=str(course.get("credits")) if course.get("credits") is not None else course.get("credits"),
        department=course.get("department"),
        prerequisites=course.get("prereqs"),
        core=course.get("core"),
    )

    if include_professors:
        professor_names = [prof for prof in course.get("professors", []) if isinstance(prof, str)]
        profiles: list[ProfessorProfile] = []
        for name in professor_names:
            raw_professor = await _load_professor(name)
            if raw_professor:
                profiles.append(_build_professor_profile(raw_professor, limit_reviews=professor_review_limit))
        details.professors = profiles

    if include_grades:
        grade_raw = await _load_course_grades(details.course_id)
        grades = [_normalize_grade_entry(entry) for entry in grade_raw[:grade_entry_limit]]
        details.grades = grades

    return details


@PLANETTERP_MCP_SERVER.tool(
    name="get_professor_profile",
    description="Fetch a professor's PlanetTerp profile and recent reviews.",
    structured_output=True,
)
async def tool_get_professor_profile(name: str, review_limit: int = 5) -> ProfessorProfile:
    if not name or not name.strip():
        raise ValueError("name is required")

    raw = await _load_professor(name.strip())
    if not raw:
        raise ValueError(f"Professor '{name}' not found on PlanetTerp.")

    return _build_professor_profile(raw, limit_reviews=review_limit)


@PLANETTERP_MCP_SERVER.tool(
    name="list_cached_courses",
    description="Return a sample of cached courses to confirm MCP readiness.",
    structured_output=True,
)
async def tool_list_cached_courses(limit: int = 10) -> Sequence[CourseSummary]:
    courses = await ensure_course_cache()
    return [_build_course_summary(course) for course in courses[:limit]]


async def call_planetterp_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Convenience wrapper around the FastMCP call interface used by the FastAPI backend."""
    arguments = arguments or {}
    return await PLANETTERP_MCP_SERVER.call_tool(name, arguments)


async def get_context(context: Context | None = None) -> Context:
    """Expose context primarily for testing convenience."""
    return context or PLANETTERP_MCP_SERVER.get_context()


def run_stdio() -> None:
    """Entry point for launching the server with stdio transport."""
    PLANETTERP_MCP_SERVER.run("stdio")


__all__ = [
    "PLANETTERP_MCP_SERVER",
    "call_planetterp_tool",
    "ensure_course_cache_warmed",
    "run_stdio",
]


if __name__ == "__main__":
    run_stdio()
