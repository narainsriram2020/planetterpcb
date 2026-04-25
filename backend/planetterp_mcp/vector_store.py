"""Qdrant-backed semantic search for PlanetTerp data."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Iterable
import re

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
except ImportError:  # pragma: no cover - optional dependency
    QdrantClient = None  # type: ignore
    Distance = VectorParams = PointStruct = Filter = FieldCondition = MatchValue = None  # type: ignore

from backend.planetterp_core import load_model

COLLECTION_NAME = "planetterp_courses"
DEFAULT_STORAGE_PATH = Path(os.getenv("PLANETTERP_QDRANT_PATH", ".planetterp_qdrant")).resolve()
DISABLE_VECTORS = os.getenv("PLANETTERP_DISABLE_VECTORS", "").lower() in {"1", "true", "yes"}

_vector_lock = asyncio.Lock()
_client: QdrantClient | None = None
_embedder = None
_cached_course_count: int | None = None
COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{4})\s*-?(\d{3}[A-Z]?)\b", re.IGNORECASE)


def _ensure_storage_path() -> None:
    DEFAULT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def _course_text(course: dict[str, Any]) -> str:
    parts = [
        course.get("course_id") or course.get("name") or "",
        course.get("title") or "",
        course.get("description") or "",
        course.get("prereqs") or "",
        course.get("core") or "",
    ]
    profs = course.get("professors") or []
    if isinstance(profs, Iterable):
        parts.extend(str(prof) for prof in profs)
    return " ".join(part for part in parts if part)


def _normalize_course_code(value: str | None) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def _extract_course_code(text: str) -> str | None:
    match = COURSE_CODE_PATTERN.search(text or "")
    if not match:
        return None
    return _normalize_course_code("".join(match.groups()))


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    def _run_encode() -> list[list[float]]:
        embeddings = _embedder.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    return await asyncio.to_thread(_run_encode)


async def _populate_qdrant(courses: list[dict[str, Any]]) -> None:
    if not courses or _client is None:
        return

    batch_size = 64
    for start in range(0, len(courses), batch_size):
        batch = courses[start : start + batch_size]
        texts = [_course_text(course) for course in batch]
        vectors = await _embed_texts(texts)
        points = []
        for course, vector in zip(batch, vectors, strict=False):
            course_id = (course.get("course_id") or course.get("name") or "").upper()
            if not course_id:
                continue
            payload = {
                "course_id": course_id,
                "normalized_code": _normalize_course_code(course_id),
                "title": course.get("title"),
                "description": course.get("description"),
                "department": course.get("department"),
                "credits": course.get("credits"),
            }
            points.append(
                PointStruct(
                    id=course_id,
                    vector=vector,
                    payload=payload,
                )
            )
        if points:
            _client.upsert(collection_name=COLLECTION_NAME, points=points)


async def ensure_vector_store(courses: list[dict[str, Any]], force_rebuild: bool = False) -> bool:
    """Ensure the Qdrant collection exists and contains embeddings for every course."""
    if DISABLE_VECTORS:
        print("ℹ️  Semantic index disabled via PLANETTERP_DISABLE_VECTORS.")
        return False

    if QdrantClient is None:
        print("⚠️  qdrant-client not installed; skipping semantic index.")
        return False

    global _client, _embedder, _cached_course_count

    async with _vector_lock:
        if _embedder is None:
            _embedder = load_model()
            if _embedder is None:
                print("⚠️  SentenceTransformer model unavailable; skipping semantic index.")
                return False

        if _client is None:
            _ensure_storage_path()
            _client = QdrantClient(path=str(DEFAULT_STORAGE_PATH))

        needs_rebuild = force_rebuild or _cached_course_count != len(courses)
        if not needs_rebuild:
            try:
                info = _client.get_collection(COLLECTION_NAME)
                if info.points_count < len(courses):
                    needs_rebuild = True
            except Exception:
                needs_rebuild = True

        if needs_rebuild:
            dim = _embedder.get_sentence_embedding_dimension()
            _client.recreate_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            await _populate_qdrant(courses)
            _cached_course_count = len(courses)
            print(f"✅ Semantic index ready with {_cached_course_count} courses")

        return True


async def semantic_course_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return semantic matches for a free-form query."""
    if (
        not query
        or not query.strip()
        or QdrantClient is None
        or _client is None
        or _embedder is None
        or DISABLE_VECTORS
    ):
        return []

    matches: list[dict[str, Any]] = []
    seen: set[str] = set()

    normalized_code = _extract_course_code(query)
    if normalized_code and Filter is not None:
        try:
            exact_filter = Filter(
                must=[
                    FieldCondition(
                        key="normalized_code",
                        match=MatchValue(value=normalized_code),
                    )
                ]
            )
            points, _ = _client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=exact_filter,
                limit=limit,
                with_payload=True,
            )
            for point in points:
                payload = point.payload or {}
                cid = (payload.get("course_id") or "").upper()
                if not cid or cid in seen:
                    continue
                payload.setdefault("score", 1.0)
                matches.append(payload)
                seen.add(cid)
                if len(matches) >= limit:
                    return matches
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Qdrant exact-match lookup failed: {exc}")

    vectors = await _embed_texts([query])
    if not vectors:
        return matches

    results = _client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vectors[0],
        limit=limit,
        with_payload=True,
    )

    for hit in results:
        payload = hit.payload or {}
        cid = (payload.get("course_id") or "").upper()
        if not cid or cid in seen:
            continue
        payload["score"] = float(hit.score)
        matches.append(payload)
        seen.add(cid)
        if len(matches) >= limit:
            break
    return matches
