from __future__ import annotations

from backend.planetterp_mcp.mcp_stub import Tool, ToolResult
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import re

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


class QdrantTools:
    COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{4})\s*-?(\d{3}[A-Z]?)\b", re.IGNORECASE)

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    @Tool(
        name="semantic_course_search",
        description="Search PlanetTerp courses semantically by topic or keyword.",
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    )
    def semantic_course_search(self, query: str, limit: int = 10) -> ToolResult:
        limit = max(1, min(limit or 10, 50))
        formatted: list[dict] = []
        seen: set[str] = set()

        normalized_code = self._extract_course_code(query or "")
        if normalized_code:
            exact_hits = self._fetch_by_normalized_code(normalized_code, limit)
            for payload in exact_hits:
                cid = (payload.get("course_id") or "").upper()
                if cid in seen:
                    continue
                formatted.append(payload)
                seen.add(cid)
                if len(formatted) >= limit:
                    return ToolResult(content=formatted)

        vector = self.model.encode(query)
        results = self.client.search(
            collection_name="courses",
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
        for hit in results:
            payload = hit.payload or {}
            cid = (payload.get("course_id") or "").upper()
            if not cid or cid in seen:
                continue
            payload.setdefault("score", float(hit.score))
            formatted.append(payload)
            seen.add(cid)
            if len(formatted) >= limit:
                break

        return ToolResult(content=formatted)

    @classmethod
    def _normalize_code(cls, value: str | None) -> str:
        return "".join(ch for ch in (value or "").upper() if ch.isalnum())

    @classmethod
    def _extract_course_code(cls, text: str) -> str | None:
        match = cls.COURSE_CODE_PATTERN.search(text or "")
        if not match:
            return None
        return cls._normalize_code("".join(match.groups()))

    def _fetch_by_normalized_code(self, normalized_code: str, limit: int) -> list[dict]:
        try:
            filters = models.Filter(
                must=[
                    models.FieldCondition(
                        key="normalized_code",
                        match=models.MatchValue(value=normalized_code),
                    )
                ]
            )
            points, _ = self.client.scroll(
                collection_name="courses",
                scroll_filter=filters,
                limit=limit,
                with_payload=True,
            )
            return [point.payload for point in points if point.payload]
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Qdrant exact-match lookup failed: {exc}")
            return []
