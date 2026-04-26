# app/schemas/chat.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatCreate(BaseModel):
    name: str

class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True
