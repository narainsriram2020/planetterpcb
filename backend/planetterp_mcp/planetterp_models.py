"""Typed structures exposed through the PlanetTerp MCP server."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CourseSummary(BaseModel):
    """Lightweight representation returned by search tools."""

    course_id: str = Field(..., description="Unique PlanetTerp course identifier e.g. CMSC131")
    title: Optional[str] = Field(None, description="Human readable title")
    description: Optional[str] = Field(None, description="Short description")
    department: Optional[str] = Field(None, description="Owning department code")
    credits: Optional[str] = Field(None, description="Credit information as reported by PlanetTerp")
    score: Optional[float] = Field(None, description="Similarity score when available")


class GradeBreakdown(BaseModel):
    """Single grade distribution entry for a course."""

    semester: Optional[str] = Field(None, description="Semester code e.g. 202308")
    section: Optional[str] = Field(None, description="Section identifier if available")
    average_gpa: Optional[float] = Field(None, description="Average GPA for the section")
    a_plus: Optional[int] = Field(None, alias="A+")
    a: Optional[int] = Field(None, alias="A")
    a_minus: Optional[int] = Field(None, alias="A-")
    b_plus: Optional[int] = Field(None, alias="B+")
    b: Optional[int] = Field(None, alias="B")
    b_minus: Optional[int] = Field(None, alias="B-")
    c_plus: Optional[int] = Field(None, alias="C+")
    c: Optional[int] = Field(None, alias="C")
    c_minus: Optional[int] = Field(None, alias="C-")
    d_plus: Optional[int] = Field(None, alias="D+")
    d: Optional[int] = Field(None, alias="D")
    d_minus: Optional[int] = Field(None, alias="D-")
    f: Optional[int] = Field(None, alias="F")
    withdrawals: Optional[int] = Field(None, alias="W")

    class Config:
        populate_by_name = True


class ProfessorReview(BaseModel):
    """Normalized professor review."""

    created: Optional[str] = Field(None, description="Review creation timestamp")
    rating: Optional[float] = Field(None, description="Numerical rating if available")
    difficulty: Optional[float] = Field(None, description="Difficulty rating")
    comment: Optional[str] = Field(None, description="Full review text")


class ProfessorProfile(BaseModel):
    """Professor details as exposed through PlanetTerp MCP."""

    name: str
    average_rating: Optional[float] = Field(None, description="Average rating across reviews")
    rating_emoji: Optional[str] = Field(None, description="Emoji describing the rating bucket")
    department: Optional[str] = Field(None, description="Primary department")
    courses: list[str] = Field(default_factory=list, description="Courses the professor teaches")
    num_reviews: Optional[int] = Field(None, description="Total review count")
    reviews: list[ProfessorReview] = Field(default_factory=list, description="Recent reviews, newest first")


class CourseDetails(BaseModel):
    """Complete course information returned by the MCP."""

    course_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    credits: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[str] = None
    core: Optional[str] = None
    professors: list[ProfessorProfile] = Field(default_factory=list)
    grades: list[GradeBreakdown] = Field(default_factory=list)


class CourseIdExtraction(BaseModel):
    """Result payload for course id extraction tool."""

    course_ids: list[str] = Field(default_factory=list, description="Detected PlanetTerp course identifiers")
