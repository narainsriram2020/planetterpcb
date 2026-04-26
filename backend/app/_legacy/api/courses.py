# app/api/courses.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.course import CourseResponse, ProfessorResponse, GradeResponse, CourseSearchResponse
from app.services.planetterp_service import PlanetTerpService
from app.services.search_service import SearchService
from app.dependencies import get_current_user_optional

router = APIRouter()

# Initialize services
planet_terp_service = PlanetTerpService()
search_service = SearchService()

@router.get("/courses", response_model=List[CourseResponse])
async def get_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all courses with pagination"""
    courses = planet_terp_service.get_courses()
    return courses[skip:skip + limit]

@router.get("/courses/search", response_model=CourseSearchResponse)
async def search_courses(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """Search for courses using semantic search"""
    # Initialize search service if needed
    if search_service.index is None:
        courses = planet_terp_service.get_courses()
        search_service.initialize_index(courses)
    
    # Perform search
    search_data = search_service.search_courses(q, planet_terp_service)
    
    return CourseSearchResponse(
        query=q,
        results=search_data["courses"],
        total=len(search_data["courses"])
    )

@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    db: Session = Depends(get_db)
):
    """Get specific course details"""
    course = planet_terp_service.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.get("/courses/{course_id}/grades", response_model=List[GradeResponse])
async def get_course_grades(
    course_id: str,
    db: Session = Depends(get_db)
):
    """Get grades for a specific course"""
    grades = planet_terp_service.get_course_grades(course_id)
    return grades

@router.get("/professors/{professor_name}", response_model=ProfessorResponse)
async def get_professor(
    professor_name: str,
    db: Session = Depends(get_db)
):
    """Get professor details"""
    professor = planet_terp_service.get_professor(professor_name)
    if not professor:
        raise HTTPException(status_code=404, detail="Professor not found")
    return professor

@router.get("/extract-course-ids")
async def extract_course_ids(
    query: str = Query(..., description="Text to extract course IDs from"),
    db: Session = Depends(get_db)
):
    """Extract course IDs from a text query"""
    course_ids = planet_terp_service.extract_course_ids(query)
    return {"course_ids": course_ids}
