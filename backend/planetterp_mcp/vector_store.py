"""Semantic search over the PlanetTerp index stored in Qdrant.

Uses Qdrant Cloud when QDRANT_URL + QDRANT_API_KEY are set, otherwise an
embedded on-disk instance at QDRANT_PATH. The index is built by
scripts/scrape_and_index.py.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from . import config

logger = logging.getLogger(__name__)

# Qdrant's embedded mode and the ONNX embedder are not designed for concurrent
# use from many threads, so every blocking call goes through one worker.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vector-store")
_ready: bool | None = None


def course_point_id(course_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"course:{course_id.upper()}"))


def professor_point_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"professor:{name.lower()}"))


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    if config.use_cloud_qdrant():
        client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY, timeout=10)
    else:
        config.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(config.QDRANT_PATH))
    # Close explicitly; the local client's __del__ fails noisily during interpreter shutdown.
    atexit.register(client.close)
    return client


@lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    return TextEmbedding(config.EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in get_embedder().embed(texts)]


def describe_backend() -> str:
    return "qdrant-cloud" if config.use_cloud_qdrant() else f"qdrant-local ({config.QDRANT_PATH})"


def _check_ready() -> bool:
    try:
        client = get_client()
        if not client.collection_exists(config.COLLECTION_NAME):
            logger.warning(
                "Qdrant collection '%s' not found on %s; run scripts/scrape_and_index.py",
                config.COLLECTION_NAME,
                describe_backend(),
            )
            return False
        count = client.count(config.COLLECTION_NAME, exact=False).count
        get_embedder()
        logger.info("Vector store ready: %s points on %s", count, describe_backend())
        return count > 0
    except Exception as exc:  # noqa: BLE001 - any failure means "fall back"
        logger.warning("Vector store unavailable on %s: %s", describe_backend(), exc)
        return False


async def is_ready(refresh: bool = False) -> bool:
    """Whether semantic search can be used. The result is cached once it succeeds."""
    global _ready
    if _ready and not refresh:
        return True
    _ready = await asyncio.get_running_loop().run_in_executor(_executor, _check_ready)
    return _ready


def _search(query: str, limit: int, query_filter: Filter) -> list[dict[str, Any]]:
    vector = embed([query])[0]
    response = get_client().query_points(
        collection_name=config.COLLECTION_NAME,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    return [{**(point.payload or {}), "score": round(point.score, 4)} for point in response.points]


async def search_courses(query: str, limit: int = 8, department: str | None = None) -> list[dict[str, Any]]:
    # Older indexes only tag professor points, so exclude those rather than
    # requiring type == "course".
    must = []
    if department:
        must.append(FieldCondition(key="department", match=MatchValue(value=department.upper())))
    query_filter = Filter(
        must=must,
        must_not=[FieldCondition(key="type", match=MatchValue(value="professor"))],
    )
    return await asyncio.get_running_loop().run_in_executor(
        _executor, _search, query, limit, query_filter
    )


async def search_professors(query: str, limit: int = 5) -> list[dict[str, Any]]:
    query_filter = Filter(must=[FieldCondition(key="type", match=MatchValue(value="professor"))])
    return await asyncio.get_running_loop().run_in_executor(
        _executor, _search, query, limit, query_filter
    )
