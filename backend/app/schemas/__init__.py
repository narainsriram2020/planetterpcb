# app/schemas/__init__.py
from .user import UserCreate, UserResponse, UserLogin
from .chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from .course import CourseResponse, ProfessorResponse, GradeResponse, CourseSearchResponse

__all__ = [
    "UserCreate", "UserResponse", "UserLogin",
    "ChatCreate", "ChatResponse", "MessageCreate", "MessageResponse",
    "CourseResponse", "ProfessorResponse", "GradeResponse", "CourseSearchResponse"
]
