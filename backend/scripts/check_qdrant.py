"""Quick check: how much data is in the Qdrant collection."""
import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env)

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

print("Collections:")
for c in client.get_collections().collections:
    info = client.get_collection(c.name)
    print(f"  {c.name}: {info.points_count} points (status: {info.status})")

# Sample a few points
try:
    points, _ = client.scroll(collection_name="planetterp", limit=3, with_payload=True)
    print("\nSample points:")
    for p in points:
        payload = p.payload or {}
        if payload.get("type") == "professor":
            print(f"  [PROF] {payload.get('name')} — rating {payload.get('average_rating')}")
        else:
            print(f"  [COURSE] {payload.get('course_id')} — {payload.get('title')} (GPA: {payload.get('average_gpa')})")
except Exception as e:
    print(f"Could not sample: {e}")
