# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.chat import Chat, Message
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.services.planetterp_service import PlanetTerpService
from app.services.gemini_service import GeminiService
from app.services.search_service import SearchService
from app.dependencies import get_current_user

router = APIRouter()

# Initialize services
planet_terp_service = PlanetTerpService()
gemini_service = GeminiService()
search_service = SearchService()

@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat"""
    chat = Chat(
        name=chat_data.name,
        user_id=current_user.id
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.get("/chats", response_model=List[ChatResponse])
async def get_user_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chats for the current user"""
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.updated_at.desc()).all()
    return chats

@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific chat"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return chat

@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a chat and get AI response"""
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Save user message
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=message_data.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Initialize search service if needed
    if search_service.index is None:
        courses = planet_terp_service.get_courses()
        search_service.initialize_index(courses)
    
    # Search for relevant courses and data
    search_data = search_service.search_courses(message_data.content, planet_terp_service)
    
    # Get chat history for context
    chat_history = []
    recent_messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.desc()).limit(10).all()
    
    for msg in reversed(recent_messages):
        chat_history.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Generate AI response
    ai_response = gemini_service.generate_response(
        message_data.content,
        search_data,
        chat_history
    )
    
    # Save AI response
    ai_message = Message(
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        metadata=search_data
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    
    return ai_message

@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific chat"""
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.asc()).all()
    
    return messages

@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully"}
