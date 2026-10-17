"""Turn MCP tool results into compact "cards" the frontend renders next to an answer."""

from __future__ import annotations

from typing import Any

GRADE_BUCKETS = ("A", "B", "C", "D", "F", "W")
MAX_PROFESSOR_BARS = 6
MAX_LIST_ITEMS = 5


def _flatten(value: Any) -> list[str]:
    """PlanetTerp geneds come as nested lists like [["DSHS", "DVUP"]]."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    flat: list[str] = []
    for item in value:
        flat.extend(_flatten(item))
    return list(dict.fromkeys(flat))


def _snippet(text: str | None, limit: int = 220) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _grades_card(payload: dict[str, Any]) -> dict[str, Any]:
    distribution = payload.get("distribution") or {}
    buckets = {bucket: 0 for bucket in GRADE_BUCKETS}
    for grade, count in distribution.items():
        bucket = grade[0] if grade[0] in buckets else None
        if bucket:
            buckets[bucket] += int(count or 0)
    professors = [
        {
            "name": p["professor"],
            "gpa": p["average_gpa"],
            "students": p["students"],
            "last_taught": p["last_taught"],
        }
        for p in payload.get("by_professor") or []
        if p.get("average_gpa") is not None and p.get("students") and p.get("professor") != "Unknown"
    ][:MAX_PROFESSOR_BARS]
    professors.sort(key=lambda p: p["gpa"], reverse=True)
    return {
        "kind": "grades",
        "key": f"grades:{payload.get('course_id')}",
        "course_id": payload.get("course_id"),
        "semesters": payload.get("semesters"),
        "average_gpa": payload.get("average_gpa"),
        "students": payload.get("students"),
        "distribution": [{"grade": g, "count": c} for g, c in buckets.items()],
        "professors": professors,
    }


def _professor_card(payload: dict[str, Any]) -> dict[str, Any]:
    reviews = payload.get("recent_reviews") or []
    review = next((r for r in reviews if (r.get("review") or "").strip()), None)
    return {
        "kind": "professor",
        "key": f"professor:{payload.get('name')}",
        "name": payload.get("name"),
        "rating": payload.get("average_rating"),
        "review_count": payload.get("review_count"),
        "courses": (payload.get("courses") or [])[:8],
        "review": {
            "course": review.get("course"),
            "rating": review.get("rating"),
            "date": review.get("date"),
            "text": _snippet(review.get("review")),
        } if review else None,
        "url": payload.get("planetterp_url"),
    }


def _course_card(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "course",
        "key": f"course:{payload.get('course_id')}",
        "course_id": payload.get("course_id"),
        "title": payload.get("title"),
        "credits": payload.get("credits"),
        "average_gpa": payload.get("average_gpa"),
        "geneds": _flatten(payload.get("geneds")),
        "professor_count": payload.get("professor_count"),
        "description": _snippet(payload.get("description")),
        "url": payload.get("planetterp_url"),
    }


def _course_list_card(arguments: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    results = [r for r in payload.get("results") or [] if r.get("course_id")][:MAX_LIST_ITEMS]
    if not results:
        return None
    return {
        "kind": "course_list",
        "key": f"course_list:{arguments.get('query')}",
        "query": arguments.get("query"),
        "results": [
            {"course_id": r["course_id"], "title": r.get("title"), "average_gpa": r.get("average_gpa")}
            for r in results
        ],
    }


def _professor_list_card(arguments: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any] | None:
    results = [r for r in payload.get("results") or [] if r.get("name")][:MAX_LIST_ITEMS]
    if not results:
        return None
    return {
        "kind": "professor_list",
        "key": f"professor_list:{arguments.get('query')}",
        "query": arguments.get("query"),
        "results": [
            {"name": r["name"], "rating": r.get("average_rating"), "review_count": r.get("review_count")}
            for r in results
        ],
    }


def card_from_tool(name: str, arguments: dict[str, Any], payload: dict[str, Any], ok: bool) -> dict[str, Any] | None:
    """Build a display card for a successful tool call, or None if it has nothing to show."""
    if not ok or not isinstance(payload, dict):
        return None
    try:
        if name == "get_grade_distribution":
            return _grades_card(payload)
        if name == "get_professor":
            return _professor_card(payload)
        if name == "get_course":
            return _course_card(payload)
        if name == "search_courses":
            return _course_list_card(arguments, payload)
        if name == "search_professors":
            return _professor_list_card(arguments, payload)
    except (KeyError, TypeError, ValueError, IndexError):
        return None  # a malformed payload shouldn't break the answer
    return None
