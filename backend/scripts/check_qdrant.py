"""Quick check: what's in the Qdrant collection (cloud or local)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planetterp_mcp import config  # noqa: E402
from planetterp_mcp.vector_store import describe_backend, get_client  # noqa: E402

client = get_client()
print(f"Backend: {describe_backend()}")
for c in client.get_collections().collections:
    print(f"  {c.name}: {client.count(c.name).count} points")

if client.collection_exists(config.COLLECTION_NAME):
    points, _ = client.scroll(collection_name=config.COLLECTION_NAME, limit=3, with_payload=True)
    print("\nSample points:")
    for p in points:
        payload = p.payload or {}
        if payload.get("type") == "professor":
            print(f"  [PROF] {payload.get('name')} — rating {payload.get('average_rating')}")
        else:
            print(f"  [COURSE] {payload.get('course_id')} — {payload.get('title')} (GPA: {payload.get('average_gpa')})")

client.close()
