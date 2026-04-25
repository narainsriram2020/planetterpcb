#!/usr/bin/env python3
"""
Example of how to integrate the backend API with a frontend
"""
import requests
import json
from typing import Dict, Any, List

class PlanetTerpChatbotAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        response = self.session.post(
            f"{self.base_url}/auth/register",
            json={"username": username, "email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Registration failed: {response.text}")
    
    def login(self, username: str, password: str) -> str:
        """Login and get access token"""
        response = self.session.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return self.token
        else:
            raise Exception(f"Login failed: {response.text}")
    
    def create_chat(self, name: str) -> Dict[str, Any]:
        """Create a new chat"""
        response = self.session.post(
            f"{self.base_url}/chat/chats",
            json={"name": name}
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create chat: {response.text}")
    
    def send_message(self, chat_id: int, message: str) -> Dict[str, Any]:
        """Send a message to a chat and get AI response"""
        response = self.session.post(
            f"{self.base_url}/chat/chats/{chat_id}/messages",
            json={"content": message}
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to send message: {response.text}")
    
    def get_chats(self) -> List[Dict[str, Any]]:
        """Get all user chats"""
        response = self.session.get(f"{self.base_url}/chat/chats")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get chats: {response.text}")
    
    def search_courses(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for courses"""
        response = self.session.get(
            f"{self.base_url}/courses/search",
            params={"q": query, "limit": limit}
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to search courses: {response.text}")
    
    def get_course_details(self, course_id: str) -> Dict[str, Any]:
        """Get course details"""
        response = self.session.get(f"{self.base_url}/courses/{course_id}")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get course details: {response.text}")

# Example usage
def main():
    """Example of how to use the API client"""
    api = PlanetTerpChatbotAPI()
    
    try:
        # Register and login (or just login if user exists)
        try:
            api.register("testuser", "test@example.com", "testpassword")
            print("✅ User registered successfully")
        except Exception as e:
            if "already registered" in str(e):
                print("ℹ️  User already exists, logging in...")
            else:
                raise e
        
        # Login
        api.login("testuser", "testpassword")
        print("✅ User logged in successfully")
        
        # Create a chat
        chat = api.create_chat("Test Chat")
        chat_id = chat["id"]
        print(f"✅ Chat created with ID: {chat_id}")
        
        # Send a message
        response = api.send_message(chat_id, "Tell me about CMSC131")
        print(f"✅ AI Response: {response['content'][:100]}...")
        
        # Search for courses
        search_results = api.search_courses("computer science", limit=3)
        print(f"✅ Found {search_results['total']} courses")
        
        # Get course details
        if search_results['results']:
            course_id = search_results['results'][0]['course_id']
            course_details = api.get_course_details(course_id)
            print(f"✅ Course details: {course_details['title']}")
        
        print("\n🎉 All API calls successful!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
