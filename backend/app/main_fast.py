from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any


import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.api_core import exceptions as google_exceptions
from pydantic import BaseModel

# === Load environment ===
load_dotenv()
project_env = Path(__file__).resolve().parents[2] / ".env"
if project_env.exists():
    load_dotenv(project_env)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MCP_BASE_URL = "http://127.0.0.1:8001/mcp"

# === FastAPI setup ===
app = FastAPI(title="PlanetTerp Chatbot (MCP HTTP-powered)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_model = None
MAX_GEMINI_RETRIES = 3
INITIAL_RETRY_DELAY = 1.5
MAX_COURSE_DETAIL_LIMIT = 10
POPULAR_COURSE_IDS = [
    "CMSC131",
    "CMSC132",
    "CMSC216",
    "CMSC250",
    "CMSC330",
    "MATH140",
    "MATH141",
    "ENGL101",
    "INST201",
    "BMGT289I",
    "ECON200",
    "PSYC100",
]


# === Schema ===
class Query(BaseModel):
    prompt: str


# === Helper: MCP HTTP call ===
async def call_planetterp_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                f"{MCP_BASE_URL}/invoke",
                json={"tool_name": name, "arguments": arguments or {}},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result")
        except Exception as exc:
            print(f"⚠️ MCP call failed for {name}: {exc}")
            return None


# === Startup ===
@app.on_event("startup")
async def startup() -> None:
    global gemini_model
    print("🚀 Starting PlanetTerp Chatbot backend...")

    if GEMINI_API_KEY:
        try:
            gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            print("✅ Gemini model loaded")
        except Exception as exc:
            print(f"❌ Gemini model failed: {exc}")

    print("✅ Ready to connect to MCP at", MCP_BASE_URL)


# === Routes ===
@app.get("/")
async def root() -> dict[str, Any]:
    return {"message": "PlanetTerp Chatbot API", "status": "running", "mode": "MCP-HTTP"}


@app.get("/health")
async def health() -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{MCP_BASE_URL}/list_tools")
            res.raise_for_status()
            tools = res.json().get("tools", [])
        except Exception:
            tools = []
    return {"status": "healthy", "mcp_tools": tools}


@app.post("/chat")
async def chat(req: Query) -> dict[str, Any]:
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    start_time = time.time()
    prompt = req.prompt.strip()
    search_limit = _determine_search_limit(prompt)
    popularity_request = _is_popularity_request(prompt)

    # --- 1️⃣ Semantic search via MCP ---
    search_hits = await call_planetterp_tool(
        "semantic_course_search",
        {"query": prompt, "limit": search_limit},
    )
    if search_hits is None:
        search_hits = []

    manual_course_ids = _extract_course_ids(prompt)
    if manual_course_ids:
        augmented_hits = []
        seen_ids = set()
        for cid in manual_course_ids:
            norm = cid.upper().replace(" ", "").replace("-", "")
            if norm and norm not in seen_ids:
                augmented_hits.append({"course_id": norm})
                seen_ids.add(norm)
        # keep manual matches ahead of semantic hits
        search_hits = augmented_hits + search_hits
    if popularity_request:
        search_hits = _inject_popular_hits(search_hits)

    professor_name = _extract_professor_name(prompt)
    professor_profile = None
    if professor_name:
        professor_profile = await _fetch_professor_profile(professor_name)

    # --- 2️⃣ Fetch details for top courses ---
    detail_limit = _determine_detail_limit(search_limit)
    course_details = []
    if (search_hits or popularity_request) and detail_limit:
        unique_course_ids: list[str] = []
        candidate_hits = list(search_hits)
        if popularity_request:
            candidate_hits = _merge_popular_priority_hits(candidate_hits)

        for hit in candidate_hits:
            cid = (hit.get("course_id") or "").strip()
            if not cid:
                continue
            cid = cid.upper()
            if cid in unique_course_ids:
                continue
            unique_course_ids.append(cid)
            if len(unique_course_ids) >= detail_limit:
                break

        if unique_course_ids:
            detail_tasks = [
                call_planetterp_tool("get_course_details", {"course_id": cid})
                for cid in unique_course_ids
            ]
            detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            for result in detail_results:
                if isinstance(result, Exception):
                    print(f"⚠️ Failed to fetch course details: {result}")
                    continue
                if result:
                    course_details.append(result)

    payload = {
        "semantic_results": search_hits,
        "course_details": course_details,
        "professor_profile": professor_profile,
        "professor_query": professor_name,
    }

    # --- 3️⃣ Try Gemini with retry ---
    reply = None
    if gemini_model:
        full_prompt = f"""
            You are "Terpy", a friendly and knowledgeable University of Maryland course assistant.
            Your job is to answer questions about UMD classes and professors using the data below.

            --- CONTEXT RULES ---
            1. Use the PlanetTerp data faithfully — never make up facts or fake statistics.
            2. When the data includes courses, summarize key info:
            - course_id and full title
            - short 1–2 line description
            - mention average GPA if available
            - mention 1–2 notable professors or trends (e.g., “challenging but fair grading”)
            3. When the data includes professors, include:
            - full name, department, rating, and emoji if available
            - what they teach or are best known for
            - a short insight like “students say...” or “most reviews mention...”
            4. If multiple results exist, group or compare briefly.
            5. If a course or professor isn't found, say that clearly and encourage checking PlanetTerp.

            --- STYLE GUIDE ---
            - Write conversationally, like a UMD student talking to another.
            - Stay concise (under 200 words total).
            - Avoid markdown, lists, or headings — just natural sentences.
            - Be confident and direct; avoid filler like “I think” or “it seems”.
            - Never say “according to the data below”; integrate it naturally.

            --- INPUT DATA ---
            User question: {prompt}

            PlanetTerp Data (JSON):
            {json.dumps(payload, indent=2)}

            Now, respond in one clean, well-written paragraph that best answers the user question.
            """

        try:
            reply = await _call_gemini_with_retry(full_prompt)
        except google_exceptions.ResourceExhausted:
            reply = None
        except Exception as exc:
            print(f"⚠️ Gemini failed: {exc}")
            reply = None

    # --- 4️⃣ Fallback if Gemini failed ---
    if not reply:
        reply = _format_planetterp_summary(payload, prompt)

    elapsed = time.time() - start_time
    print(f"⏱️ Response time: {elapsed:.2f}s")

    return {
        "reply": reply,
        "course_details": course_details,
        "processing_time": f"{elapsed:.2f}s",
    }


async def _call_gemini_with_retry(full_prompt: str) -> str:
    """Async-safe retry wrapper for Gemini with exponential backoff."""
    delay = INITIAL_RETRY_DELAY
    last_exc: Exception | None = None

    for attempt in range(MAX_GEMINI_RETRIES):
        try:
            response = gemini_model.generate_content(
                [{"role": "user", "parts": [full_prompt]}],
                generation_config={"temperature": 0.5, "max_output_tokens": 400},
            )
            if response and response.text:
                return response.text.strip()
        except google_exceptions.ResourceExhausted as exc:
            last_exc = exc
            print(f"⚠️ Gemini busy (attempt {attempt+1}/{MAX_GEMINI_RETRIES}). Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as e:
            last_exc = e
            print(f"❌ Gemini error: {e}")
            break

    # optional: fallback to a smaller model
    try:
        alt_model = genai.GenerativeModel("gemini-1.5-flash")
        response = alt_model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    raise last_exc or RuntimeError("Gemini failed after retries.")


def _format_planetterp_summary(payload: dict[str, Any], prompt: str | None = None) -> str:
    """Readable fallback summary if Gemini fails."""
    details = payload.get("course_details") or []
    semantic = payload.get("semantic_results") or []

    lines: list[str] = []
    listed_ids: set[str] = set()

    if prompt:
        lines.append(
            f"Here’s what PlanetTerp shows for your request about '{prompt.strip()}':"
        )
        lines.append("")

    professor_profile = payload.get("professor_profile")
    if professor_profile:
        lines.append("Professor profile:")
        prof_name = professor_profile.get("name") or payload.get("professor_query") or "Unknown professor"
        avg_rating = professor_profile.get("average_rating")
        emoji = professor_profile.get("rating_emoji") or ""
        dept = professor_profile.get("department") or "Unknown department"
        num_reviews = professor_profile.get("num_reviews")
        rating_text = (
            f"{avg_rating:.2f}" if isinstance(avg_rating, (int, float)) else "N/A"
        )
        review_text = f"{num_reviews} reviews" if isinstance(num_reviews, int) else "reviews unavailable"
        lines.append(f"- {prof_name} {emoji} ({dept}) — rating {rating_text} across {review_text}.")
        courses = ", ".join(professor_profile.get("courses") or []) or "No courses listed"
        lines.append(f"  Recent courses: {courses}.")
        reviews = professor_profile.get("reviews") or []
        if reviews:
            lines.append("  Recent student notes:")
            for review in reviews[:2]:
                comment = (review.get("comment") or review.get("review") or "").strip()
                if not comment:
                    continue
                created = review.get("created")
                rating = review.get("rating")
                meta = []
                if rating is not None:
                    meta.append(f"rating {rating}")
                if created:
                    meta.append(created)
                prefix = f"    • ({', '.join(meta)}) " if meta else "    • "
                lines.append(prefix + comment[:240])
        lines.append("")

    if details:
        lines.append("Top matches:")
        for entry in details:
            course = entry.get("course", {})
            name = course.get("name") or course.get("course_id") or "Unknown course"
            if isinstance(name, str):
                listed_ids.add(name.upper())
            title = course.get("title") or "No title"
            avg_gpa = course.get("average_gpa")
            profs = ", ".join(course.get("professors") or []) or "No professors listed"
            gpa_text = (
                f"average GPA {avg_gpa:.2f}"
                if isinstance(avg_gpa, (int, float))
                else "average GPA not reported"
            )
            lines.append(f"- {name}: {title}. {gpa_text}. Recently taught by {profs}.")
        lines.append("")

    if semantic:
        extras: list[str] = []
        for hit in semantic:
            cid = (hit.get("course_id") or "").upper()
            if not cid or cid in listed_ids:
                continue
            title = hit.get("title") or ""
            dept = hit.get("department") or ""
            extras.append(f"{cid}{' - ' + title if title else ''} [{dept}]")
            if len(extras) >= 12:
                break
        if extras:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("More PlanetTerp matches you can explore:")
            lines.extend(f"- {extra}" for extra in extras)
            lines.append("")

    if not lines:
        return "PlanetTerp did not return any relevant courses for that question."
    return "\n".join(line for line in lines if line is not None)


async def _fetch_professor_profile(name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    try:
        profile = await call_planetterp_tool("get_professor_profile", {"name": name})
        return profile
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Failed to load professor profile for {name}: {exc}")
        return None


def _extract_professor_name(prompt: str) -> str | None:
    """Heuristically extract a professor name from the prompt."""
    if not prompt:
        return None

    # Bail if the query clearly targets a course id
    if re.search(r"\b[A-Z]{4}\d{3}[A-Z]?\b", prompt.upper()):
        return None

    patterns = [
        r"(?:professor|prof\.?|teacher)\s+([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+)+)",
        r"(?:tell me about|who is|info(?:rmation)? on|what can you tell me about|details about)\s+([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+)+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback: grab the last proper noun sequence if the prompt is short
    tokens = re.findall(r"\b([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+)+)\b", prompt)
    if tokens and len(prompt.split()) <= 12:
        return tokens[-1].strip()

    return None


def _extract_course_ids(prompt: str) -> list[str]:
    if not prompt:
        return []
    return re.findall(r"\b[A-Z]{4}\s*-?\d{3}[A-Z]?\b", prompt.upper())


def _determine_search_limit(prompt: str) -> int:
    """Scale semantic search depth based on how broad the user's request is."""
    baseline = 8
    normalized = prompt.lower()
    broad_keywords = [
        "all ",
        "every",
        "list",
        "show me",
        "give me",
        "gimme",
        "catalog",
    ]
    dept_codes = re.findall(r"\b[A-Z]{4}\b", prompt.upper())
    mentions_courses = "course" in normalized or "class" in normalized
    has_broad_keyword = any(keyword in normalized for keyword in broad_keywords)

    if dept_codes and has_broad_keyword:
        return 30
    if dept_codes and mentions_courses:
        return 18
    if has_broad_keyword:
        return 12
    if "professor" in normalized and "course" not in normalized:
        return 6
    return baseline


def _determine_detail_limit(search_limit: int) -> int:
    """Cap expensive detail lookups to keep latency reasonable."""
    if search_limit >= 25:
        return 4
    if search_limit >= 18:
        return 5
    if search_limit >= 12:
        return 6
    return min(MAX_COURSE_DETAIL_LIMIT, 6)


def _is_popularity_request(prompt: str) -> bool:
    if not prompt:
        return False
    normalized = prompt.lower()
    popularity_keywords = [
        "most popular",
        "most famous",
        "popular class",
        "famous class",
        "everyone takes",
        "best class",
        "best course",
        "must take",
        "crowd favorite",
        "most taken",
    ]
    if any(keyword in normalized for keyword in popularity_keywords):
        return True
    if "popular" in normalized and "class" in normalized:
        return True
    return False


def _inject_popular_hits(existing_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing_hits or [])
    seen = { (hit.get("course_id") or "").upper() for hit in merged if hit.get("course_id") }
    for cid in POPULAR_COURSE_IDS:
        if cid.upper() in seen:
            continue
        merged.append(
            {
                "course_id": cid,
                "title": None,
                "department": cid[:4],
                "description": "Highly requested course at UMD.",
            }
        )
        seen.add(cid.upper())
    return merged


def _merge_popular_priority_hits(existing_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    for cid in POPULAR_COURSE_IDS:
        key = cid.upper()
        if key in seen:
            continue
        ordered.append({"course_id": key})
        seen.add(key)

    for hit in existing_hits:
        cid = (hit.get("course_id") or "").upper()
        if not cid or cid in seen:
            continue
        ordered.append(hit)
        seen.add(cid)

    return ordered
