# app/models/__init__.py
from .user import User
from .chat import Chat, Message
from .course import Course, Professor, Grade

__all__ = ["User", "Chat", "Message", "Course", "Professor", "Grade"]
