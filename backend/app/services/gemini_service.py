# app/services/gemini_service.py
import google.generativeai as genai
import json
from typing import Dict, Any, List
from app.config import settings

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    def generate_response(self, query: str, data: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> str:
        """Generate a response using Gemini AI"""
        try:
            # Prepare the system prompt
            system_prompt = self._get_system_prompt()
            
            # Add rating emojis to professors
            if "professors" in data:
                for prof in data["professors"]:
                    if "average_rating" in prof:
                        prof["rating_emoji"] = self._get_rating_emoji(prof["average_rating"])
                    else:
                        prof["rating_emoji"] = "❓"
            
            # Prepare context
            context = {
                "courses": data.get("courses", []),
                "professors": data.get("professors", []),
                "grades": data.get("grades", [])
            }
            
            # Create the prompt
            prompt = f"""
            PlanetTerp Data: {json.dumps(context, indent=2)}
            Question: {query}
            """
            
            # Configure generation settings
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            # Safety settings
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            # Generate response
            response = self.model.generate_content(
                system_prompt + prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            return response.text
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try asking your question again."
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI assistant"""
        return """
        You are a UMD assistant using PlanetTerp data. Be concise but helpful about courses and professors.
        Focus on the most recent grades, ratings, and recommendations from the past 3-4 years (2021-2025).
        Explicitly mention the recency of the data (e.g., "According to Spring 2024 data...").
        Remember context from previous questions. Keep in mind what class or professors you have already suggested during the conversation and use that as context. 
        Do not bring up random data out of nowhere continue conversation on whatever data is being currently discussed. 
        If you don't have information about a specific course or professor, simply say so and explain that
        they should visit the PlanetTerp website to get more info, but this should be the last resort option.
        Sound very laid back and chill like you are another student.
        When a student asks about what professor they should take for a certain course give them your personal evaluation of the best professor.
        When mentioning professors, always include their rating emoji beside their name using this format:
        Professor Name [emoji] - where emoji indicates their average rating.
        """
    
    def _get_rating_emoji(self, rating: float) -> str:
        """Convert numerical rating to emoji for visual representation"""
        if not rating or rating < 0:
            return "❓"  # Unknown rating
        elif rating >= 4.5:
            return "🌟"  # Excellent
        elif rating >= 4.0:
            return "⭐"  # Very Good
        elif rating >= 3.0:
            return "✅"  # Good/Average
        elif rating >= 2.0:
            return "⚠️"  # Below Average
        else:
            return "❗"  # Poor
    
    def generate_chat_name(self, query: str) -> str:
        """Generate a chat name based on the first query"""
        # Extract course IDs
        course_ids = self._extract_course_ids(query)
        if course_ids:
            return f"{', '.join(course_ids)} Question"
        
        # Use first few words
        words = query.split()
        if len(words) <= 4:
            return query
        else:
            return ' '.join(words[:4]) + "..."
    
    def _extract_course_ids(self, query: str) -> List[str]:
        """Extract course IDs from a query string"""
        import re
        pattern = r'\b[A-Z]{4}\d{3}[A-Z]?\b'
        matches = re.findall(pattern, query.upper())
        return matches
    
    def get_greeting(self) -> str:
        """Get appropriate greeting based on time of day"""
        import datetime
        hour = datetime.datetime.now().hour
        if hour > 5 and hour < 11:
            return "Good morning"
        elif hour >= 11 and hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"
