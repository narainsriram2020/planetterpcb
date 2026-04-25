# planetterp_core.py
import requests
import re
import os
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

DISABLE_VECTORS = os.getenv("PLANETTERP_DISABLE_VECTORS", "").lower() in {"1", "true", "yes"}

# Optional ML imports
if not DISABLE_VECTORS:
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        import faiss
        ML_AVAILABLE = True
    except ImportError:
        ML_AVAILABLE = False
        print("Warning: ML libraries not available. Semantic search will be disabled.")
else:
    ML_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: Google Generative AI not available.")

load_dotenv()
project_env = Path(__file__).resolve().parents[1] / ".env"
if project_env.exists():
    load_dotenv(project_env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
PLANETTERP_BASE_URL = "https://planetterp.com/api/v1"

def get_courses():
    response = requests.get(f"{PLANETTERP_BASE_URL}/courses")
    if response.status_code == 200:
        return response.json()
    return []

def get_course(course_id):
    response = requests.get(f"{PLANETTERP_BASE_URL}/course", params={"name": course_id})
    if response.status_code == 200:
        return response.json()
    return None

def get_professor(name):
    response = requests.get(f"{PLANETTERP_BASE_URL}/professor", 
                           params={"name": name, "reviews": "true"})
    if response.status_code == 200:
        professor_data = response.json()
        # Sort reviews by recency
        return sort_professor_reviews(professor_data)
    return None

def sort_professor_reviews(professor_data):
    if professor_data and 'reviews' in professor_data and professor_data['reviews']:
        # Sort reviews by date in descending order
        professor_data['reviews'].sort(key=lambda x: x.get('created', ''), reverse=True)
    return professor_data

def filter_recent_grades(grades, years=4):
    # Get current year
    current_year = datetime.datetime.now().year
    
    recent_grades = [g for g in grades if g.get('semester') and 
                    int(g.get('semester', '000000')[:4]) >= (current_year - years)]

    recent_grades.sort(key=lambda x: x.get('semester', '000000'), reverse=True)
    
    return recent_grades

def get_course_grades(course_id):
    response = requests.get(f"{PLANETTERP_BASE_URL}/grades", params={"course": course_id})
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            return []
        return filter_recent_grades(data)
    return []

def extract_course_ids(query):
    # Look for standard course patterns like CMSC330, MATH140, etc.
    pattern = r'\b[A-Z]{4}\d{3}[A-Z]?\b'
    matches = re.findall(pattern, query.upper())
    return matches

# Model and semantic search functions
def load_model():
    if not ML_AVAILABLE:
        return None
    try:
        import torch
        torch.set_num_threads(1)  # Reduce thread usage
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def initialize_index(model, courses):
    if not ML_AVAILABLE or not model or not courses:
        return None, []
        
    try:
        # Create descriptions
        texts = []
        ids = []
        for course in courses:
            course_id = course.get('course_id') or course.get('name')
            title = course.get('title', '')
            desc = course.get('description', '')
            texts.append(f"{course_id}: {title}. {desc}")
            ids.append(course_id)
        
        # Create embeddings
        embeddings = model.encode(texts)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings).astype('float32'))
        
        return index, ids
    except Exception as e:
        print(f"Error initializing index: {e}")
        return None, []

def search(query, index, course_ids, model, k=5):
    if not ML_AVAILABLE or index is None or model is None:
        return []
    
    try:
        query_embedding = model.encode([query])
        _, indices = index.search(
            np.array(query_embedding).astype('float32'), k
        )
        
        results = []
        for idx in indices[0]:
            if idx < len(course_ids):
                course_id = course_ids[idx]
                if course_id not in results:  # Avoid duplicates
                    results.append(course_id)
        
        return results
    except Exception as e:
        print(f"Error during search: {e}")
        return []

def get_rating_emoji(rating):
    """Convert numerical rating to emoji for visual representation"""
    if not rating or rating < 0:
        return " ❓"  # Unknown rating
    elif rating >= 4.5:
        return " 🌟"  # Excellent
    elif rating >= 4.0:
        return " ⭐"  # Very Good
    elif rating >= 3.0:
        return " ✅"  # Good/Average
    elif rating >= 2.0:
        return " ⚠️"  # Below Average
    else:
        return " ❗"  # Poor
