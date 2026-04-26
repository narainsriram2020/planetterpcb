"""
PlanetTerp → Qdrant Cloud Scraper & Indexer

Scrapes everything from PlanetTerp (courses, professors, grades, reviews)
and indexes it into a Qdrant Cloud cluster with semantic embeddings.

Usage:
    cd backend
    py scripts/scrape_and_index.py
"""

from __future__ import annotations

import os
import sys
import json
import uuid
from pathlib import Path

import requests
import time
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
    PayloadSchemaType,
)
from sentence_transformers import SentenceTransformer

# Load .env from project root
load_dotenv()
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PLANETTERP_BASE = "https://planetterp.com/api/v1"
COLLECTION_NAME = "planetterp"
EMBED_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 64
PAGE_TIMEOUT = 60       # generous timeout per page request
GRADE_TIMEOUT = 12      # shorter for the high-volume grades endpoint
PARALLEL_WORKERS = 4    # be gentle with PlanetTerp — fewer parallel = fewer timeouts
GRADE_WORKERS = 6
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
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "planetterp-scraper/1.0"})
    return s


SESSION = _make_session()


# ── PlanetTerp API helpers ─────────────────────────────────────────────────

def pt_get_page(path: str, params: dict, timeout: int = PAGE_TIMEOUT) -> tuple[int, list[dict] | None]:
    """Fetch one page. Returns (offset, results) where results is None on failure."""
    url = f"{PLANETTERP_BASE}/{path.lstrip('/')}"
    offset = params.get("offset", 0)
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return offset, data
            return offset, []
        if r.status_code == 404:
            return offset, []  # legitimately empty
    except Exception:
        pass
    return offset, None  # signal failure (different from empty)


def _fetch_with_relentless_retry(
    endpoint: str,
    estimated_total: int,
    extra_params: dict | None = None,
) -> list[dict]:
    """
    Fetch all pages, retrying any that fail until they succeed
    or we hit MAX_RETRY_ROUNDS. Empty pages (legitimate end) are not retried.
    """
    limit = 100
    all_offsets = list(range(0, estimated_total + limit, limit))
    succeeded: dict[int, list[dict]] = {}
    pending: set[int] = set(all_offsets)

    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        if not pending:
            break

        # On later rounds, drop parallelism and add backoff
        workers = max(1, PARALLEL_WORKERS - (round_num - 1) // 2)
        delay = 1.0 * (round_num - 1)  # 0s, 1s, 2s... between requests on retry rounds
        print(f"  Round {round_num}: {len(pending)} pages to fetch, {workers} workers, {delay}s pacing")

        failed_this_round: set[int] = set()
        offsets_this_round = sorted(pending)
        items_count = sum(len(p) for p in succeeded.values())

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = []
            for i, o in enumerate(offsets_this_round):
                if delay > 0 and i > 0:
                    time.sleep(delay / max(workers, 1))
                params = {"limit": limit, "offset": o, **(extra_params or {})}
                futures.append(pool.submit(pt_get_page, endpoint, params))

            done = 0
            for fut in futures:
                offset, page = fut.result()
                if page is None:
                    failed_this_round.add(offset)
                else:
                    succeeded[offset] = page
                    items_count += len(page)
                done += 1
                if done % 25 == 0:
                    print(f"    {done}/{len(offsets_this_round)} pages, {items_count} items so far...")

        pending = failed_this_round
        if pending:
            print(f"  Round {round_num} done — {len(pending)} pages still failing")

    if pending:
        print(f"  WARNING: {len(pending)} pages permanently failed after {MAX_RETRY_ROUNDS} rounds")

    items = []
    for o in sorted(succeeded):
        items.extend(succeeded[o])
    return items


def fetch_all_courses() -> list[dict]:
    print("Fetching courses (relentless mode)...")
    courses = _fetch_with_relentless_retry("courses", estimated_total=18000)
    print(f"Total courses: {len(courses)}")
    return courses


def fetch_all_professors() -> list[dict]:
    print("Fetching professors (relentless mode, with reviews)...")
    professors = _fetch_with_relentless_retry(
        "professors", estimated_total=4000, extra_params={"reviews": "true"}
    )
    print(f"Total professors: {len(professors)}")
    return professors


def fetch_grades(course_id: str) -> list[dict] | None:
    """Returns None on failure, [] for legitimately empty, list for data."""
    url = f"{PLANETTERP_BASE}/grades"
    try:
        r = SESSION.get(url, params={"course": course_id}, timeout=GRADE_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            return []
        if r.status_code == 404:
            return []
    except Exception:
        pass
    return None


def fetch_all_grades(course_ids: list[str]) -> dict[str, list[dict]]:
    """Fetch grades for all courses with retry rounds for failures."""
    grade_map: dict[str, list[dict]] = {}
    pending: set[str] = set(course_ids)
    total = len(course_ids)

    def _fetch(cid: str) -> tuple[str, list[dict] | None]:
        return cid, fetch_grades(cid)

    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        if not pending:
            break

        workers = max(1, GRADE_WORKERS - (round_num - 1))
        delay = 0.3 * (round_num - 1)
        print(f"\nGrades round {round_num}: {len(pending)} courses to fetch ({workers} workers)...")

        failed: set[str] = set()
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = []
            for i, cid in enumerate(sorted(pending)):
                if delay > 0 and i > 0:
                    time.sleep(delay / max(workers, 1))
                futures.append(pool.submit(_fetch, cid))
            for fut in futures:
                cid, grades = fut.result()
                if grades is None:
                    failed.add(cid)
                else:
                    grade_map[cid] = grades
                done += 1
                if done % 500 == 0:
                    print(f"  {done}/{len(pending)} this round, {len(grade_map)}/{total} total...")

        pending = failed
        if pending:
            print(f"  {len(pending)} courses still failing after round {round_num}")

    print(f"  Done. Got grade data for {sum(1 for g in grade_map.values() if g)} courses.")
    if pending:
        print(f"  WARNING: {len(pending)} courses permanently failed grade fetch")
    return grade_map


def compute_average_gpa(grade_entries: list[dict]) -> float | None:
    """Compute weighted average GPA across all grade entries."""
    total_students = 0
    weighted_sum = 0.0
    grade_points = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "D-": 0.7,
        "F": 0.0,
    }
    for entry in grade_entries:
        for grade, points in grade_points.items():
            count = entry.get(grade, 0) or 0
            weighted_sum += count * points
            total_students += count
    if total_students == 0:
        return None
    return round(weighted_sum / total_students, 2)


# ── Embedding ──────────────────────────────────────────────────────────────

def build_course_text(course: dict, grades: list[dict], prof_map: dict[str, dict]) -> str:
    """Build a rich text blob for embedding — more info = better search."""
    parts = []

    course_id = course.get("course_id") or course.get("name") or ""
    title = course.get("title") or ""
    desc = course.get("description") or ""
    dept = course.get("department") or ""
    credits = course.get("credits")
    prereqs = course.get("prereqs") or ""
    core = course.get("core") or ""

    parts.append(f"{course_id}: {title}.")
    if desc:
        parts.append(desc)
    if dept:
        parts.append(f"Department: {dept}.")
    if credits:
        parts.append(f"{credits} credits.")
    if prereqs:
        parts.append(f"Prerequisites: {prereqs}.")
    if core:
        parts.append(f"GenEd: {core}.")

    # GPA
    avg_gpa = compute_average_gpa(grades)
    if avg_gpa is not None:
        parts.append(f"Average GPA: {avg_gpa}.")

    # Professors
    prof_names = [p for p in (course.get("professors") or []) if isinstance(p, str)]
    if prof_names:
        parts.append(f"Taught by: {', '.join(prof_names[:10])}.")
        # Inject professor ratings/reviews into text for better semantic search
        for name in prof_names[:5]:
            prof = prof_map.get(name.lower())
            if not prof:
                continue
            rating = prof.get("average_rating")
            if rating:
                parts.append(f"{name} has a rating of {rating:.1f}/5.")
            reviews = prof.get("reviews") or []
            for review in reviews[:2]:
                comment = (review.get("review") or "").strip()
                if comment and len(comment) > 20:
                    parts.append(f'Student about {name}: "{comment[:200]}"')

    return " ".join(parts)


# ── Qdrant helpers ─────────────────────────────────────────────────────────

def get_client() -> QdrantClient:
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("ERROR: QDRANT_URL and QDRANT_API_KEY must be set in .env")
        sys.exit(1)
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def recreate_collection(client: QdrantClient, dim: int) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Deleting existing '{COLLECTION_NAME}' collection...")
        client.delete_collection(COLLECTION_NAME)
    print(f"Creating '{COLLECTION_NAME}' collection (dim={dim})...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    # Index key payload fields for fast filtering
    client.create_payload_index(COLLECTION_NAME, "course_id", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "department", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "normalized_code", PayloadSchemaType.KEYWORD)


def upsert_batch(client: QdrantClient, points: list[PointStruct]) -> None:
    client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("PlanetTerp → Qdrant Cloud Indexer")
    print("=" * 60)

    # 1. Fetch all data
    courses = fetch_all_courses()
    professors = fetch_all_professors()

    # Build professor lookup by lowercase name
    prof_map: dict[str, dict] = {}
    for prof in professors:
        name = (prof.get("name") or "").strip()
        if name:
            prof_map[name.lower()] = prof

    # 2. Fetch grades for all courses in parallel
    course_ids = [
        (c.get("course_id") or c.get("name") or "").upper()
        for c in courses
        if (c.get("course_id") or c.get("name"))
    ]
    grade_map = fetch_all_grades(course_ids)

    # 3. Load embedding model
    print(f"\nLoading embedding model ({EMBED_MODEL})...")
    model = SentenceTransformer(EMBED_MODEL)
    dim = model.get_sentence_embedding_dimension()
    print(f"Embedding dimension: {dim}")

    # 4. Connect to Qdrant and set up collection
    print(f"\nConnecting to Qdrant at {QDRANT_URL}...")
    client = get_client()
    recreate_collection(client, dim)

    # 5. Build and upload course points
    print(f"\nEmbedding and uploading {len(courses)} courses...")
    batch_texts: list[str] = []
    batch_payloads: list[dict] = []
    batch_ids: list[str] = []
    total_uploaded = 0

    def flush_batch():
        nonlocal total_uploaded
        if not batch_texts:
            return
        vectors = model.encode(
            batch_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()
        points = [
            PointStruct(id=pid, vector=vec, payload=payload)
            for pid, vec, payload in zip(batch_ids, vectors, batch_payloads)
        ]
        upsert_batch(client, points)
        total_uploaded += len(points)
        print(f"  Uploaded {total_uploaded}/{len(courses)} courses...")
        batch_texts.clear()
        batch_payloads.clear()
        batch_ids.clear()

    for course in courses:
        cid = (course.get("course_id") or course.get("name") or "").strip().upper()
        if not cid:
            continue

        grades = grade_map.get(cid, [])
        avg_gpa = compute_average_gpa(grades)
        text = build_course_text(course, grades, prof_map)
        normalized_code = "".join(ch for ch in cid if ch.isalnum())

        payload = {
            "course_id": cid,
            "normalized_code": normalized_code,
            "title": course.get("title"),
            "description": course.get("description"),
            "department": course.get("department"),
            "credits": course.get("credits"),
            "prereqs": course.get("prereqs"),
            "core": course.get("core"),
            "professors": [p for p in (course.get("professors") or []) if isinstance(p, str)],
            "average_gpa": avg_gpa,
            "grade_entries": grades[:6],  # store recent semesters
        }

        batch_texts.append(text)
        batch_payloads.append(payload)
        batch_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, f"course:{cid}")))

        if len(batch_texts) >= BATCH_SIZE:
            flush_batch()

    flush_batch()

    # 6. Upload professor points (separate IDs prefixed with "prof_")
    print(f"\nEmbedding and uploading {len(professors)} professors...")
    prof_batch_texts: list[str] = []
    prof_batch_payloads: list[dict] = []
    prof_batch_ids: list[str] = []
    total_profs = 0

    def flush_prof_batch():
        nonlocal total_profs
        if not prof_batch_texts:
            return
        vectors = model.encode(
            prof_batch_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()
        points = [
            PointStruct(id=pid, vector=vec, payload=payload)
            for pid, vec, payload in zip(prof_batch_ids, vectors, prof_batch_payloads)
        ]
        upsert_batch(client, points)
        total_profs += len(points)
        print(f"  Uploaded {total_profs}/{len(professors)} professors...")
        prof_batch_texts.clear()
        prof_batch_payloads.clear()
        prof_batch_ids.clear()

    for prof in professors:
        name = (prof.get("name") or "").strip()
        if not name:
            continue

        reviews = prof.get("reviews") or []
        rating = prof.get("average_rating")
        dept = prof.get("department") or ""
        courses_taught = [c for c in (prof.get("courses") or []) if isinstance(c, str)]

        # Build rich text for professor
        text_parts = [f"Professor {name}."]
        if dept:
            text_parts.append(f"Department: {dept}.")
        if courses_taught:
            text_parts.append(f"Teaches: {', '.join(courses_taught[:15])}.")
        if rating:
            text_parts.append(f"Rating: {rating:.1f}/5.")
        for review in reviews[:5]:
            comment = (review.get("review") or "").strip()
            if comment and len(comment) > 15:
                text_parts.append(f'"{comment[:300]}"')

        # Use a string ID for professors (Qdrant supports string IDs)
        safe_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"professor:{name.lower()}"))

        prof_batch_texts.append(" ".join(text_parts))
        prof_batch_ids.append(safe_id)
        prof_batch_payloads.append({
            "type": "professor",
            "name": name,
            "department": dept,
            "average_rating": rating,
            "courses": courses_taught,
            "num_reviews": len(reviews),
            "reviews": [
                {
                    "rating": r.get("rating"),
                    "review": (r.get("review") or "")[:400],
                    "created": r.get("created"),
                }
                for r in reviews[:10]
            ],
        })

        if len(prof_batch_texts) >= BATCH_SIZE:
            flush_prof_batch()

    flush_prof_batch()

    # 7. Summary
    info = client.get_collection(COLLECTION_NAME)
    print("\n" + "=" * 60)
    print("Done!")
    print(f"  Collection : {COLLECTION_NAME}")
    print(f"  Total points: {info.points_count}")
    print(f"  Courses indexed : {total_uploaded}")
    print(f"  Professors indexed: {total_profs}")
    print("=" * 60)


if __name__ == "__main__":
    main()
