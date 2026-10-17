"""
PlanetTerp → Qdrant scraper & indexer

Fetches every course and professor (with reviews) from PlanetTerp, embeds
them with all-MiniLM-L6-v2 (via fastembed), and writes them to the
"planetterp" collection: Qdrant Cloud when QDRANT_URL + QDRANT_API_KEY are
set, otherwise the local on-disk store at QDRANT_PATH (default backend/.qdrant).

Usage:
    cd backend
    py scripts/scrape_and_index.py                          # everything
    py scripts/scrape_and_index.py --departments CMSC,MATH  # quick dev index
    py scripts/scrape_and_index.py --local                  # force local store
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PLANETTERP_BASE = "https://planetterp.com/api/v1"
BATCH_SIZE = 64
PAGE_SIZE = 100
PAGE_TIMEOUT = 60       # generous timeout per page request
PARALLEL_WORKERS = 4    # be gentle with PlanetTerp — fewer parallel = fewer timeouts
MAX_RETRY_ROUNDS = 8    # keep retrying failed pages until everything succeeds


# ── HTTP session with connection pooling and HTTP-level retries ──────────

def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "planetterp-chatbot-indexer"})
    return s


SESSION = _make_session()


# ── PlanetTerp API helpers ─────────────────────────────────────────────────

def pt_get_page(path: str, params: dict) -> tuple[int, list[dict] | None]:
    """Fetch one page. Returns (offset, results) where results is None on failure."""
    offset = params.get("offset", 0)
    try:
        r = SESSION.get(f"{PLANETTERP_BASE}/{path}", params=params, timeout=PAGE_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return offset, data if isinstance(data, list) else []
        if r.status_code == 404:
            return offset, []  # legitimately empty
    except Exception:
        pass
    return offset, None  # signal failure (different from empty)


def fetch_all(endpoint: str, extra_params: dict | None = None) -> list[dict]:
    """
    Page through an endpoint until an empty/short page, retrying failed pages
    for up to MAX_RETRY_ROUNDS rounds.
    """
    succeeded: dict[int, list[dict]] = {}
    pending: set[int] = set()
    next_offset = 0
    exhausted = False

    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        # Probe forward in windows until a short page shows we've reached the end.
        while not exhausted:
            window = [next_offset + i * PAGE_SIZE for i in range(PARALLEL_WORKERS * 4)]
            next_offset = window[-1] + PAGE_SIZE
            pages = _fetch_pages(endpoint, window, extra_params, PARALLEL_WORKERS)
            for offset, page in pages:
                if page is None:
                    pending.add(offset)
                else:
                    succeeded[offset] = page
                    if len(page) < PAGE_SIZE:
                        exhausted = True
            print(f"  {endpoint}: {sum(len(p) for p in succeeded.values())} items so far...")

        if not pending:
            break
        workers = max(1, PARALLEL_WORKERS - round_num // 2)
        print(f"  Retry round {round_num}: {len(pending)} failed pages, {workers} workers")
        time.sleep(round_num)
        retry = _fetch_pages(endpoint, sorted(pending), extra_params, workers)
        pending = {offset for offset, page in retry if page is None}
        succeeded.update({offset: page for offset, page in retry if page is not None})

    if pending:
        print(f"  WARNING: {len(pending)} pages permanently failed after {MAX_RETRY_ROUNDS} rounds")

    items = []
    for offset in sorted(succeeded):
        items.extend(succeeded[offset])
    return items


def _fetch_pages(endpoint: str, offsets: list[int], extra_params: dict | None, workers: int):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(pt_get_page, endpoint, {"limit": PAGE_SIZE, "offset": o, **(extra_params or {})})
            for o in offsets
        ]
        return [f.result() for f in futures]


def fetch_courses(departments: list[str] | None) -> list[dict]:
    if not departments:
        return fetch_all("courses")
    courses = []
    for dept in departments:
        courses.extend(fetch_all("courses", {"department": dept}))
    return courses


def fetch_professors() -> list[dict]:
    return fetch_all("professors", {"reviews": "true"})


# ── Embedding text ─────────────────────────────────────────────────────────

def build_course_text(course: dict, prof_map: dict[str, dict], clean_text) -> str:
    """Build a rich text blob for embedding — more info = better search."""
    course_id = course.get("name") or ""
    parts = [f"{course_id}: {course.get('title') or ''}."]
    if course.get("description"):
        parts.append(clean_text(course["description"]))
    if course.get("department"):
        parts.append(f"Department: {course['department']}.")
    if course.get("credits"):
        parts.append(f"{course['credits']} credits.")
    if course.get("geneds"):
        parts.append(f"GenEd: {course['geneds']}.")
    if isinstance(course.get("average_gpa"), (int, float)):
        parts.append(f"Average GPA: {course['average_gpa']:.2f}.")

    prof_names = list(dict.fromkeys(p for p in (course.get("professors") or []) if isinstance(p, str)))
    if prof_names:
        parts.append(f"Taught by: {', '.join(prof_names[:10])}.")
        # Professor ratings and review snippets make "chill"/"hard" queries work.
        for name in prof_names[:5]:
            prof = prof_map.get(name.lower())
            if not prof:
                continue
            if prof.get("average_rating"):
                parts.append(f"{name} has a rating of {prof['average_rating']:.1f}/5.")
            for review in (prof.get("reviews") or [])[:2]:
                comment = clean_text(review.get("review"))
                if len(comment) > 20:
                    parts.append(f'Student about {name}: "{comment[:200]}"')
    return " ".join(parts)


def build_professor_text(prof: dict, clean_text) -> str:
    parts = [f"Professor {prof['name']}."]
    courses = list(dict.fromkeys(c for c in (prof.get("courses") or []) if isinstance(c, str)))
    if courses:
        parts.append(f"Teaches: {', '.join(courses[:15])}.")
    if prof.get("average_rating"):
        parts.append(f"Rating: {prof['average_rating']:.1f}/5.")
    for review in (prof.get("reviews") or [])[:5]:
        comment = clean_text(review.get("review"))
        if len(comment) > 15:
            parts.append(f'"{comment[:300]}"')
    return " ".join(parts)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--departments", help="Comma-separated department codes to index (default: all)")
    parser.add_argument("--local", action="store_true", help="Write to the local on-disk store even if cloud is configured")
    args = parser.parse_args()
    if args.local:
        os.environ["QDRANT_MODE"] = "local"

    # Imported after QDRANT_MODE is set so config picks it up.
    from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

    from planetterp_mcp import config
    from planetterp_mcp.planetterp_api import clean_text
    from planetterp_mcp.vector_store import (
        course_point_id, describe_backend, embed, get_client, professor_point_id,
    )

    departments = [d.strip().upper() for d in args.departments.split(",")] if args.departments else None

    print("=" * 60)
    print(f"PlanetTerp → {describe_backend()}")
    print("=" * 60)

    print("Fetching courses...")
    courses = fetch_courses(departments)
    print(f"Total courses: {len(courses)}")
    print("Fetching professors (with reviews)...")
    professors = fetch_professors()
    print(f"Total professors: {len(professors)}")

    if departments:
        prefixes = tuple(departments)
        professors = [
            p for p in professors
            if any(isinstance(c, str) and c.startswith(prefixes) for c in p.get("courses") or [])
        ]
        print(f"Professors teaching {', '.join(departments)}: {len(professors)}")

    prof_map = {p["name"].strip().lower(): p for p in professors if p.get("name")}

    points: list[PointStruct] = []
    texts: list[str] = []
    for course in courses:
        cid = (course.get("name") or "").strip().upper()
        if not cid:
            continue
        texts.append(build_course_text(course, prof_map, clean_text))
        points.append(PointStruct(
            id=course_point_id(cid),
            vector=[],
            payload={
                "type": "course",
                "course_id": cid,
                "normalized_code": cid,
                "title": course.get("title"),
                "description": clean_text(course.get("description")),
                "department": course.get("department"),
                "credits": course.get("credits"),
                "geneds": course.get("geneds"),
                "average_gpa": course.get("average_gpa"),
                "is_recent": course.get("is_recent"),
                "professors": list(dict.fromkeys(p for p in (course.get("professors") or []) if isinstance(p, str))),
            },
        ))

    for prof in professors:
        name = (prof.get("name") or "").strip()
        if not name:
            continue
        reviews = prof.get("reviews") or []
        texts.append(build_professor_text({**prof, "name": name}, clean_text))
        points.append(PointStruct(
            id=professor_point_id(name),
            vector=[],
            payload={
                "type": "professor",
                "name": name,
                "average_rating": prof.get("average_rating"),
                "courses": list(dict.fromkeys(c for c in (prof.get("courses") or []) if isinstance(c, str))),
                "num_reviews": len(reviews),
            },
        ))

    client = get_client()
    dim = len(embed(["dimension probe"])[0])
    if client.collection_exists(config.COLLECTION_NAME):
        print(f"Deleting existing '{config.COLLECTION_NAME}' collection...")
        client.delete_collection(config.COLLECTION_NAME)
    client.create_collection(
        collection_name=config.COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    if config.use_cloud_qdrant():  # payload indexes are a no-op in local mode
        for key in ("type", "course_id", "department", "normalized_code"):
            client.create_payload_index(config.COLLECTION_NAME, key, PayloadSchemaType.KEYWORD)

    print(f"\nEmbedding and uploading {len(points)} points...")
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start : start + BATCH_SIZE]
        for point, vector in zip(batch, embed(texts[start : start + BATCH_SIZE])):
            point.vector = vector
        client.upsert(collection_name=config.COLLECTION_NAME, points=batch, wait=True)
        done = start + len(batch)
        if done % (BATCH_SIZE * 20) == 0 or done == len(points):
            print(f"  Uploaded {done}/{len(points)}")

    total = client.count(config.COLLECTION_NAME).count
    client.close()
    print("\n" + "=" * 60)
    print(f"Done! '{config.COLLECTION_NAME}' has {total} points "
          f"({len(courses)} courses, {len(prof_map)} professors) on {describe_backend()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
