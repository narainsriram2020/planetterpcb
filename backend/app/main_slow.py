from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from planetterp_core import (
    get_courses, get_course, get_professor,
    get_course_grades, extract_course_ids,
    initialize_index, search, load_model, get_rating_emoji
)

load_dotenv()
project_env = Path(__file__).resolve().parents[2] / ".env"
if project_env.exists():
    load_dotenv(project_env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = load_model()
index, course_ids = None, []

@app.on_event("startup")
async def startup():
    global index, course_ids
    print("Initializing course index...")
    courses = get_courses()
    if model:
        index, course_ids = initialize_index(model, courses)
        print("Index ready!")
    else:
        print("ML model not available. Only direct course ID search will work.")

class Query(BaseModel):
    prompt: str

@app.get("/")
async def root():
    return {"message": "PlanetTerp Chatbot API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat")
async def chat(req: Query):
    query = req.prompt
    direct = extract_course_ids(query)
    semantic = [] if direct else search(query, index, course_ids, model)
    all_ids = list(set(direct + semantic))

    data = {"courses": [], "professors": [], "grades": []}
    for cid in all_ids[:3]:
        c = get_course(cid)
        if c:
            data["courses"].append(c)
            grades = get_course_grades(cid)
            if grades: data["grades"].extend(grades[:5])
            for prof in c.get("professors", [])[:3]:
                p = get_professor(prof)
                if p: data["professors"].append(p)

    for p in data["professors"]:
        if "average_rating" in p:
            p["rating_emoji"] = get_rating_emoji(p["average_rating"])

    system_prompt = """You are a chill UMD student helping others pick classes and professors.
Be concise, funny, and use emojis for ratings. Mention recent data (2021–2025)."""

    fallback_summary = _format_planetterp_summary(data)

    try:
        # Create the prompt
        prompt = f"""
        {system_prompt}
        
        PlanetTerp Data: {json.dumps(data, indent=2)}
        
        User Question: {query}
        """
        
        reply = _generate_with_retry(prompt)
        return {"reply": reply}
    except google_exceptions.ResourceExhausted:
        return {
            "reply": (
                "Gemini is temporarily busy, here’s a quick PlanetTerp summary:\n"
                + fallback_summary
            )
        }
    except Exception as e:
        return {"reply": f"Sorry, I encountered an error: {str(e)}"}


def _generate_with_retry(prompt: str) -> str:
    """Call Gemini with retries to avoid transient 429 errors."""
    model_gemini = genai.GenerativeModel(GEMINI_MODEL_NAME)
    delay = 1.5
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = model_gemini.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
            return response.text
        except google_exceptions.ResourceExhausted as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2
        except Exception:
            raise
    raise last_exc or RuntimeError("Gemini call failed")


def _format_planetterp_summary(data: dict) -> str:
    """Provide a readable snapshot of PlanetTerp data when Gemini is unavailable."""
    courses = data.get("courses") or []
    grades = data.get("grades") or []

    lines: list[str] = []
    if courses:
        for course in courses[:3]:
            name = course.get("name") or "Unknown course"
            title = course.get("title") or "No title"
            avg_gpa = course.get("average_gpa")
            gpa_text = f"{avg_gpa:.2f}" if isinstance(avg_gpa, (int, float)) else "N/A"
            profs = ", ".join(course.get("professors") or []) or "No professors listed"
            lines.append(f"- {name}: {title} (avg GPA {gpa_text}; profs: {profs})")
    elif grades:
        lines.append("Recent grade data found, but no course metadata was available.")
    else:
        lines.append("No PlanetTerp data matched this query.")

    return "\n".join(lines)
