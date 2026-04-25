# app/models/course.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=True)
    department = Column(String, nullable=True)
    professors = Column(JSON, nullable=True)  # List of professor names
    prerequisites = Column(JSON, nullable=True)  # List of prerequisite course IDs
    corequisites = Column(JSON, nullable=True)  # List of corequisite course IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Professor(Base):
    __tablename__ = "professors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=True)
    average_rating = Column(Float, nullable=True)
    average_difficulty = Column(Float, nullable=True)
    num_ratings = Column(Integer, default=0)
    reviews = Column(JSON, nullable=True)  # List of review objects
    courses = Column(JSON, nullable=True)  # List of course IDs they teach
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Grade(Base):
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, index=True, nullable=False)
    professor_name = Column(String, nullable=True)
    semester = Column(String, nullable=False)  # Format: YYYYMM
    section = Column(String, nullable=True)
    grade_distribution = Column(JSON, nullable=False)  # {"A+": 10, "A": 20, ...}
    total_students = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
