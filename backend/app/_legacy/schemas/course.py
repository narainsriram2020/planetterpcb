# app/schemas/course.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class CourseResponse(BaseModel):
    course_id: str
    name: str
    title: str
    description: Optional[str]
    credits: Optional[int]
    department: Optional[str]
    professors: Optional[List[str]]
    prerequisites: Optional[List[str]]
    corequisites: Optional[List[str]]
    
    class Config:
        from_attributes = True

class ProfessorResponse(BaseModel):
    name: str
    department: Optional[str]
    average_rating: Optional[float]
    average_difficulty: Optional[float]
    num_ratings: int
    courses: Optional[List[str]]
    reviews: Optional[List[Dict[str, Any]]]
    
    class Config:
        from_attributes = True

class GradeResponse(BaseModel):
    course_id: str
    professor_name: Optional[str]
    semester: str
    section: Optional[str]
    grade_distribution: Dict[str, int]
    total_students: Optional[int]
    
    class Config:
        from_attributes = True

class CourseSearchResponse(BaseModel):
    query: str
    results: List[CourseResponse]
    total: int
