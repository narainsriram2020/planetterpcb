# app/services/planetterp_service.py
import requests
import datetime
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.cache_service import CacheService

class PlanetTerpService:
    def __init__(self):
        self.base_url = settings.PLANETTERP_BASE_URL
        self.cache = CacheService()
    
    def get_courses(self) -> List[Dict[str, Any]]:
        """Get all courses from PlanetTerp API"""
        cache_key = "courses_all"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            response = requests.get(f"{self.base_url}/courses", timeout=30)
            if response.status_code == 200:
                courses = response.json()
                self.cache.set(cache_key, courses, ttl=settings.CACHE_TTL)
                return courses
        except Exception as e:
            print(f"Error fetching courses: {e}")
        
        return []
    
    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get specific course details"""
        cache_key = f"course_{course_id}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            response = requests.get(f"{self.base_url}/course", 
                                  params={"name": course_id}, timeout=30)
            if response.status_code == 200:
                course = response.json()
                self.cache.set(cache_key, course, ttl=settings.CACHE_TTL)
                return course
        except Exception as e:
            print(f"Error fetching course {course_id}: {e}")
        
        return None
    
    def get_professor(self, name: str) -> Optional[Dict[str, Any]]:
        """Get professor details with reviews"""
        cache_key = f"professor_{name}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            response = requests.get(f"{self.base_url}/professor", 
                                  params={"name": name, "reviews": "true"}, timeout=30)
            if response.status_code == 200:
                professor = response.json()
                # Sort reviews by recency
                if professor and 'reviews' in professor and professor['reviews']:
                    professor['reviews'].sort(key=lambda x: x.get('created', ''), reverse=True)
                self.cache.set(cache_key, professor, ttl=settings.CACHE_TTL)
                return professor
        except Exception as e:
            print(f"Error fetching professor {name}: {e}")
        
        return None
    
    def get_course_grades(self, course_id: str) -> List[Dict[str, Any]]:
        """Get course grades with filtering for recent years"""
        cache_key = f"grades_{course_id}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            response = requests.get(f"{self.base_url}/grades", 
                                  params={"course": course_id}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "error" in data:
                    return []
                
                # Filter for recent grades (last 4 years)
                recent_grades = self._filter_recent_grades(data)
                self.cache.set(cache_key, recent_grades, ttl=settings.CACHE_TTL)
                return recent_grades
        except Exception as e:
            print(f"Error fetching grades for {course_id}: {e}")
        
        return []
    
    def _filter_recent_grades(self, grades: List[Dict[str, Any]], years: int = 4) -> List[Dict[str, Any]]:
        """Filter grades to only include recent years"""
        current_year = datetime.datetime.now().year
        
        recent_grades = [
            g for g in grades 
            if g.get('semester') and 
            int(g.get('semester', '000000')[:4]) >= (current_year - years)
        ]
        
        # Sort by semester (most recent first)
        recent_grades.sort(key=lambda x: x.get('semester', '000000'), reverse=True)
        return recent_grades
    
    def extract_course_ids(self, query: str) -> List[str]:
        """Extract course IDs from a query string"""
        import re
        pattern = r'\b[A-Z]{4}\d{3}[A-Z]?\b'
        matches = re.findall(pattern, query.upper())
        return matches
