"""Environment-driven settings shared by the MCP server, API, and indexer."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

QDRANT_URL = os.getenv("QDRANT_URL") or None
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
# Used when no cloud cluster is configured (or QDRANT_MODE=local).
QDRANT_PATH = Path(os.getenv("QDRANT_PATH") or BACKEND_DIR / ".qdrant").resolve()
QDRANT_MODE = os.getenv("QDRANT_MODE", "auto").lower()  # auto | cloud | local
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "planetterp")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def use_cloud_qdrant() -> bool:
    if QDRANT_MODE == "local":
        return False
    return bool(QDRANT_URL and QDRANT_API_KEY)
