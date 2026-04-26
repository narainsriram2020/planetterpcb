# app/models/chat.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)  # Store course data, professor info, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
