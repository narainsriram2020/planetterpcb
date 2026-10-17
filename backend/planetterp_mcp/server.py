"""PlanetTerp MCP server: UMD course, professor, and grade tools.

Built on the official MCP Python SDK. The FastAPI app mounts it at /mcp
(streamable HTTP), and it can also run standalone:

    py -m planetterp_mcp.server            # stdio, e.g. for Claude Desktop
    py -m planetterp_mcp.server --http     # streamable HTTP on :8001/mcp
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import planetterp_api as pt
from . import vector_store

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_CHARS = 600


def _transport_security() -> TransportSecuritySettings | None:
    """DNS-rebinding protection: localhost-only by default, MCP_ALLOWED_HOSTS when deployed."""
    hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if not hosts:
        return None  # FastMCP default: allow localhost only
    if hosts == ["*"]:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=[f"https://{h}" for h in hosts],
    )


mcp = FastMCP(
    "TerpGuide",
    instructions=(
        "Data about University of Maryland (UMD) courses, professors, and grade "
        "distributions from PlanetTerp. Course ids look like CMSC330 or MATH140."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=_transport_security(),
)


def _dedupe(items: list[Any]) -> list[Any]:
    return list(dict.fromkeys(item for item in items if item))


def _short(text: str | None, limit: int = MAX_DESCRIPTION_CHARS) -> str:
    text = pt.clean_text(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _round(value: Any) -> float | None:
    return round(float(value), 2) if isinstance(value, (int, float)) else None


def _course_hit(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_id": payload.get("course_id"),
        "title": payload.get("title"),
        "department": payload.get("department"),
        "credits": payload.get("credits"),
        "average_gpa": _round(payload.get("average_gpa")),
        "geneds": payload.get("geneds") or payload.get("core"),
        "description": _short(payload.get("description"), 200),
        "relevance": payload.get("score"),
    }


@mcp.tool()
async def search_courses(query: str, department: str | None = None, limit: int = 8) -> dict[str, Any]:
    """Find UMD courses matching a topic, interest, or description using semantic search.

    Use this when the student describes what they want ("easy astronomy gen ed",
    "intro machine learning", "classes about climate policy") instead of naming
    a specific course id. Results include each course's average GPA.

    Args:
        query: Natural-language description of the courses wanted.
        department: Optional 4-letter department code (e.g. "CMSC") to restrict results.
        limit: Maximum number of courses to return (1-20).
    """
    limit = max(1, min(limit, 20))
    if await vector_store.is_ready():
        hits = await vector_store.search_courses(query, limit=limit, department=department)
        return {"source": "semantic_index", "results": [_course_hit(hit) for hit in hits]}

    # Degraded mode: PlanetTerp's own name search (matches course ids/titles only).
    matches = await pt.search(query, limit=limit * 2)
    results = [
        {"course_id": m.get("name"), "title": m.get("title"), "department": m.get("department")}
        for m in matches
        if m.get("type") == "course"
        and (not department or (m.get("department") or "").upper() == department.upper())
    ][:limit]
    return {"source": "planetterp_name_search", "results": results}


@mcp.tool()
async def get_course(course_id: str) -> dict[str, Any]:
    """Get details for one UMD course: title, description, credits, prerequisites,
    GenEd categories, all-time average GPA, and professors who have taught it.

    Args:
        course_id: Course id such as "CMSC330" (spaces/dashes are fine).
    """
    course = await pt.get_course(course_id)
    if not course:
        raise ValueError(f"Course '{pt.normalize_course_id(course_id)}' was not found on PlanetTerp.")

    professors = _dedupe(course.get("professors") or [])
    return {
        "course_id": course.get("name"),
        "title": course.get("title"),
        "department": course.get("department"),
        "credits": course.get("credits"),
        "description": _short(course.get("description")),
        "geneds": course.get("geneds"),
        "average_gpa": _round(course.get("average_gpa")),
        "currently_offered": course.get("is_recent"),
        "professor_count": len(professors),
        "professors": professors[:20],
        "planetterp_url": f"https://planetterp.com/course/{course.get('name')}",
    }


@mcp.tool()
async def get_grade_distribution(
    course_id: str, professor: str | None = None, recent_semesters: int = 8
) -> dict[str, Any]:
    """Get grade distributions for a course over recent semesters, overall and broken
    down by professor. Use this to compare professors for the same course
    ("who should I take for CMSC330?") or to judge how hard a course is.

    Args:
        course_id: Course id such as "CMSC330".
        professor: Optional full professor name to restrict the data to.
        recent_semesters: How many of the most recent semesters to include (1-20).
    """
    rows = await pt.get_grades(course_id, professor=professor)
    if not rows:
        raise ValueError(f"No grade data found for {pt.normalize_course_id(course_id)}"
                         + (f" taught by {professor}" if professor else "") + ".")

    semesters = sorted({row.get("semester") for row in rows if row.get("semester")}, reverse=True)
    keep = set(semesters[: max(1, min(recent_semesters, 20))])
    rows = [row for row in rows if row.get("semester") in keep]

    overall_gpa, overall_students = pt.compute_gpa(rows)
    distribution = {
        grade: sum(int(row.get(grade) or 0) for row in rows)
        for grade in [*pt.GRADE_POINTS, "W"]
    }

    by_professor: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_professor.setdefault(row.get("professor") or "Unknown", []).append(row)

    professors = []
    for name, prof_rows in by_professor.items():
        gpa, students = pt.compute_gpa(prof_rows)
        professors.append({
            "professor": name,
            "average_gpa": gpa,
            "students": students,
            "sections": len(prof_rows),
            "last_taught": max(row.get("semester") or "" for row in prof_rows),
        })
    professors.sort(key=lambda p: (p["last_taught"], p["students"]), reverse=True)

    return {
        "course_id": pt.normalize_course_id(course_id),
        "semesters": f"{min(keep)}-{max(keep)} (YYYYMM; 01=spring, 05=summer, 08=fall, 12=winter)",
        "average_gpa": overall_gpa,
        "students": overall_students,
        "distribution": distribution,
        "by_professor": professors[:15],
    }


@mcp.tool()
async def get_professor(name: str, review_limit: int = 5) -> dict[str, Any]:
    """Get a UMD professor's PlanetTerp profile: average rating (out of 5), courses
    taught, and their most recent student reviews.

    Args:
        name: Professor's name; partial names like "Herman" are resolved by search.
        review_limit: Number of recent reviews to include (0-10).
    """
    professor = await pt.get_professor(name)
    if not professor:
        candidates = [m for m in await pt.search(name, limit=5) if m.get("type") == "professor"]
        if candidates:
            professor = await pt.get_professor(candidates[0]["name"])
    if not professor:
        raise ValueError(f"No professor named '{name}' was found on PlanetTerp.")

    reviews = sorted(professor.get("reviews") or [], key=lambda r: r.get("created") or "", reverse=True)
    return {
        "name": professor.get("name"),
        "average_rating": _round(professor.get("average_rating")),
        "review_count": len(reviews),
        "courses": sorted(_dedupe(professor.get("courses") or [])),
        "recent_reviews": [
            {
                "course": r.get("course"),
                "rating": r.get("rating"),
                "expected_grade": r.get("expected_grade"),
                "date": (r.get("created") or "")[:10],
                "review": _short(r.get("review"), 400),
            }
            for r in reviews[: max(0, min(review_limit, 10))]
        ],
        "planetterp_url": f"https://planetterp.com/professor/{professor.get('slug')}",
    }


@mcp.tool()
async def search_professors(query: str, limit: int = 5) -> dict[str, Any]:
    """Find UMD professors by name, department, or what students say about them
    (e.g. "CMSC professors known for clear lectures").

    Args:
        query: A name or a description of the kind of professor wanted.
        limit: Maximum number of professors to return (1-10).
    """
    limit = max(1, min(limit, 10))
    if await vector_store.is_ready():
        hits = await vector_store.search_professors(query, limit=limit)
        return {
            "source": "semantic_index",
            "results": [
                {
                    "name": hit.get("name"),
                    "average_rating": _round(hit.get("average_rating")),
                    "review_count": hit.get("num_reviews"),
                    "courses": _dedupe(hit.get("courses") or [])[:10],
                    "relevance": hit.get("score"),
                }
                for hit in hits
            ],
        }

    matches = await pt.search(query, limit=limit * 2)
    results = [{"name": m.get("name")} for m in matches if m.get("type") == "professor"][:limit]
    return {"source": "planetterp_name_search", "results": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--http" in sys.argv:
        mcp.settings.port = int(os.getenv("MCP_PORT", "8001"))
        mcp.settings.streamable_http_path = "/mcp"
        mcp.run("streamable-http")
    else:
        mcp.run("stdio")
