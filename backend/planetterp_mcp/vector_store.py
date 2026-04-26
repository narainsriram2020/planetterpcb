"""Qdrant-backed semantic search for PlanetTerp data.

Uses cloud Qdrant when QDRANT_URL + QDRANT_API_KEY are set,
otherwise falls back to a local on-disk instance.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env)

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
    QDRANT_AVAILABLE = True
except ImportError:
    QdrantClient = None
    QDRANT_AVAILABLE = False

from planetterp_core import load_model

COLLECTION_NAME = "planetterp"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
LOCAL_STORAGE_PATH = Path(os.getenv("PLANETTERP_QDRANT_PATH", ".planetterp_qdrant")).resolve()
DISABLE_VECTORS = os.getenv("PLANETTERP_DISABLE_VECTORS", "").lower() in {"1", "true", "yes"}
COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{4})\s*-?(\d{3}[A-Z]?)\b", re.IGNORECASE)

_vector_lock = asyncio.Lock()
_client: QdrantClient | None = None
_embedder = None
_use_cloud = bool(QDRANT_URL and QDRANT_API_KEY)


def _get_client() -> QdrantClient | None:
    global _client
    if _client is not None:
        return _client
    if not QDRANT_AVAILABLE:
        return None
    if _use_cloud:
        print(f"Connecting to cloud Qdrant at {QDRANT_URL}...")
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        LOCAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        _client = QdrantClient(path=str(LOCAL_STORAGE_PATH))
    return _client


def _normalize_code(value: str | None) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def _extract_course_code(text: str) -> str | None:
    match = COURSE_CODE_PATTERN.search(text or "")
    if not match:
        return None
    return _normalize_code("".join(match.groups()))


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts or _embedder is None:
        return []

    def _run() -> list[list[float]]:
        return _embedder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    return await asyncio.to_thread(_run)


async def ensure_vector_store(courses: list[dict[str, Any]], force_rebuild: bool = False) -> bool:
    """
    Cloud mode: just verify the collection exists — the scraper populates it.
    Local mode: build and populate the collection from the course list.
    """
    if DISABLE_VECTORS:
        return False
    if not QDRANT_AVAILABLE:
        print("qdrant-client not installed; skipping semantic index.")
        return False

    global _embedder

    async with _vector_lock:
        client = _get_client()
        if client is None:
            return False

        if _embedder is None:
            _embedder = await asyncio.to_thread(load_model)
            if _embedder is None:
                print("SentenceTransformer unavailable; skipping semantic index.")
                return False

        # Cloud mode: just confirm the collection exists
        if _use_cloud:
            try:
                info = client.get_collection(COLLECTION_NAME)
                print(f"Cloud Qdrant ready: '{COLLECTION_NAME}' has {info.points_count} points.")
                return True
            except Exception as e:
                print(f"Cloud Qdrant collection '{COLLECTION_NAME}' not found: {e}")
                print("Run: py scripts/scrape_and_index.py")
                return False

        # Local mode: build collection from courses if needed
        needs_rebuild = force_rebuild
        if not needs_rebuild:
            try:
                info = client.get_collection(COLLECTION_NAME)
                if info.points_count < len(courses):
                    needs_rebuild = True
            except Exception:
                needs_rebuild = True

        if needs_rebuild:
            dim = _embedder.get_sentence_embedding_dimension()
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            client.create_collection(
                COLLECTION_NAME,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            await _populate_local(client, courses)
            print(f"Local Qdrant ready with {len(courses)} courses.")

        return True


async def _populate_local(client: QdrantClient, courses: list[dict[str, Any]]) -> None:
    batch_size = 64
    for start in range(0, len(courses), batch_size):
        batch = courses[start : start + batch_size]
        texts = [
            " ".join(filter(None, [
                course.get("course_id") or course.get("name") or "",
                course.get("title") or "",
                course.get("description") or "",
            ]))
            for course in batch
        ]
        vectors = await _embed_texts(texts)
        points = []
        for course, vector in zip(batch, vectors):
            cid = (course.get("course_id") or course.get("name") or "").upper()
            if not cid:
                continue
            points.append(PointStruct(
                id=cid,
                vector=vector,
                payload={
                    "course_id": cid,
                    "normalized_code": _normalize_code(cid),
                    "title": course.get("title"),
                    "description": course.get("description"),
                    "department": course.get("department"),
                    "credits": course.get("credits"),
                },
            ))
        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)


async def semantic_course_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not query or not query.strip() or DISABLE_VECTORS:
        return []

    client = _get_client()
    if client is None or _embedder is None:
        return []

    matches: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Exact course code match first
    normalized_code = _extract_course_code(query)
    if normalized_code:
        try:
            exact_filter = Filter(must=[
                FieldCondition(key="normalized_code", match=MatchValue(value=normalized_code))
            ])
            points, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=exact_filter,
                limit=limit,
                with_payload=True,
            )
            for point in points:
                payload = dict(point.payload or {})
                cid = (payload.get("course_id") or "").upper()
                if not cid or cid in seen:
                    continue
                payload["score"] = 1.0
                matches.append(payload)
                seen.add(cid)
                if len(matches) >= limit:
                    return matches
        except Exception as e:
            print(f"Qdrant exact-match failed: {e}")

    # Semantic search
    vectors = await _embed_texts([query])
    if not vectors:
        return matches

    try:
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vectors[0],
            limit=limit,
            with_payload=True,
        )
        for hit in results:
            payload = dict(hit.payload or {})
            # Skip professor entries for course search
            if payload.get("type") == "professor":
                continue
            cid = (payload.get("course_id") or "").upper()
            if not cid or cid in seen:
                continue
            payload["score"] = float(hit.score)
            matches.append(payload)
            seen.add(cid)
            if len(matches) >= limit:
                break
    except Exception as e:
        print(f"Qdrant semantic search failed: {e}")

    return matches


async def semantic_professor_search(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search for professors by name or description."""
    client = _get_client()
    if client is None or _embedder is None:
        return []

    vectors = await _embed_texts([query])
    if not vectors:
        return []

    try:
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vectors[0],
            query_filter=Filter(must=[
                FieldCondition(key="type", match=MatchValue(value="professor"))
            ]),
            limit=limit,
            with_payload=True,
        )
        return [dict(hit.payload or {}) for hit in results]
    except Exception as e:
        print(f"Qdrant professor search failed: {e}")
        return []
