# app/services/search_service.py
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.cache_service import CacheService

class SearchService:
    def __init__(self):
        self.model = None
        self.index = None
        self.course_ids = []
        self.cache = CacheService()
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            self.model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
    
    def initialize_index(self, courses: List[Dict[str, Any]]) -> bool:
        """Initialize the FAISS index with course data"""
        if not courses or not self.model:
            return False
        
        try:
            # Create course descriptions
            texts = []
            ids = []
            
            for course in courses:
                course_id = course.get('course_id') or course.get('name')
                title = course.get('title', '')
                desc = course.get('description', '')
                
                # Create a searchable text
                text = f"{course_id}: {title}. {desc}"
                texts.append(text)
                ids.append(course_id)
            
            if not texts:
                return False
            
            # Create embeddings
            embeddings = self.model.encode(texts)
            dim = embeddings.shape[1]
            
            # Create FAISS index
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(np.array(embeddings).astype('float32'))
            self.course_ids = ids
            
            return True
            
        except Exception as e:
            print(f"Error initializing index: {e}")
            return False
    
    def search(self, query: str, k: int = 5) -> List[str]:
        """Search for courses using semantic similarity"""
        if not self.index or not self.model:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.model.encode([query])
            
            # Search the index
            _, indices = self.index.search(
                np.array(query_embedding).astype('float32'), k
            )
            
            # Extract course IDs
            results = []
            for idx in indices[0]:
                if idx < len(self.course_ids):
                    course_id = self.course_ids[idx]
                    if course_id not in results:  # Avoid duplicates
                        results.append(course_id)
            
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def extract_course_ids(self, query: str) -> List[str]:
        """Extract course IDs from a query string using regex"""
        import re
        pattern = r'\b[A-Z]{4}\d{3}[A-Z]?\b'
        matches = re.findall(pattern, query.upper())
        return matches
    
    def search_courses(self, query: str, planet_terp_service) -> Dict[str, Any]:
        """Comprehensive course search combining direct and semantic search"""
        # First try to extract course IDs directly from the query
        direct_course_ids = self.extract_course_ids(query)
        
        # If no direct matches, use semantic search
        semantic_course_ids = []
        if not direct_course_ids:
            semantic_course_ids = self.search(query)
        
        # Combine results
        all_course_ids = direct_course_ids + semantic_course_ids
        
        # Get course details
        data = {"courses": [], "professors": [], "grades": []}
        
        for course_id in all_course_ids[:3]:  # Limit to top 3 results
            course = planet_terp_service.get_course(course_id)
            if course:
                data["courses"].append(course)
                
                # Get grades for this course
                grades = planet_terp_service.get_course_grades(course_id)
                if grades:
                    data["grades"].extend(grades[:5])  # Limit to 5 most recent grade entries
                
                # Get professors for this course
                for prof_name in course.get("professors", [])[:5]:  # Limit to 5 professors
                    prof = planet_terp_service.get_professor(prof_name)
                    if prof:
                        data["professors"].append(prof)
        
        return data
