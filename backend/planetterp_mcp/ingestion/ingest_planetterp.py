# ingestion/ingest_planetterp.py
import requests
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv
import time
from bs4 import BeautifulSoup

#delete it
load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

client.delete_collection("courses")
print("✅ Deleted old collection.")

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PLANETTERP_API = "https://planetterp.com/api/v1"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def clean_html(text: str) -> str:
    """Remove HTML tags and fix weird characters from course descriptions."""
    try:
        soup = BeautifulSoup(text or "", "html.parser")
        clean = soup.get_text(" ", strip=True)
        return clean.encode("utf-8", errors="ignore").decode("utf-8")
    except Exception:
        return text or ""


def normalize_course_code(value: str | None) -> str:
    """Normalize course identifiers so CMSC132 / CMSC 132 / cmsc-132 all match."""
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def fetch_all_courses():
    """Fetch all unique courses from PlanetTerp API (limit/offset) safely."""
    print("📥 Fetching all courses from PlanetTerp...")
    all_courses, seen_ids = [], set()
    limit, offset, total_unique, call_count, MAX_CALLS = 100, 0, 0, 0, 200

    while True:
        if call_count >= MAX_CALLS:
            print(f"⚠️ Reached {MAX_CALLS} API calls — stopping for safety.")
            break

        try:
            res = requests.get(
                f"{PLANETTERP_API}/courses",
                params={"limit": limit, "offset": offset},
                timeout=10,
            )
            if res.status_code != 200:
                print(f"❌ Error fetching offset {offset}: {res.status_code}")
                break

            data = res.json()
            if not data:
                print("✅ Empty response — finished fetching.")
                break

            new_courses = [c for c in data if c.get("name") not in seen_ids]
            for c in new_courses:
                seen_ids.add(c.get("name"))

            total_unique = len(seen_ids)
            all_courses.extend(new_courses)
            call_count += 1
            print(f"Fetched offset {offset}: +{len(new_courses)} (total {total_unique})")

            if len(data) < limit:
                print(f"✅ Reached last partial batch at offset {offset}. Stopping.")
                break

            offset += limit
            time.sleep(0.1)

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error at offset {offset}: {e}")
            break

    print(f"📚 Total unique courses fetched: {total_unique}")
    return all_courses


def ingest_courses_to_qdrant():
    """Embed and upload all courses to Qdrant."""
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")

        courses = fetch_all_courses()
        if not courses:
            print("⚠️ No courses fetched. Exiting.")
            return

        print(f"Fetched {len(courses)} courses total.")

        texts, payloads = [], []
        for c in courses:
            name = c.get("name", "")
            title = c.get("title", "")
            desc = clean_html(c.get("description", "")) or ""
            text = f"{name} {title}. {desc}".strip()

            texts.append(text)
            payloads.append({
                "course_id": name,
                "normalized_code": normalize_course_code(name),
                "title": title,
                "description": desc,
                "department": c.get("department", ""),
                "credits": c.get("credits", ""),
            })

        print("🧠 Generating embeddings...")
        embeddings = np.array(model.encode(texts, show_progress_bar=True, batch_size=32), dtype=np.float32)

        if not client.collection_exists("courses"):
            print("🧱 Creating Qdrant collection...")
            client.create_collection(
                collection_name="courses",
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
            )
        else:
            print("♻️ Updating existing collection...")

        print("📤 Uploading to Qdrant in batches...")
        batch_size = 256
        total_uploaded = 0

        for i in range(0, len(embeddings), batch_size):
            batch_vectors = embeddings[i:i + batch_size]
            batch_payloads = payloads[i:i + batch_size]

            points = [
                models.PointStruct(
                    id=abs(hash(p["course_id"])) % (10**9),  # deterministic IDs
                    vector=v.tolist(),
                    payload=p,
                )
                for v, p in zip(batch_vectors, batch_payloads)
            ]

            client.upsert(collection_name="courses", points=points)
            total_uploaded += len(points)
            print(f"  → Uploaded {total_uploaded} / {len(embeddings)}")

        print("✅ All courses successfully ingested into Qdrant!")
        print("📊 Qdrant now contains:",
              client.count(collection_name="courses", exact=True).count, "points")

    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        raise


if __name__ == "__main__":
    ingest_courses_to_qdrant()
