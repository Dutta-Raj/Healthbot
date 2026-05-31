# main_api_with_db.py (updated version with MongoDB)
"""
HealthBot AI - Main API with MongoDB Atlas Integration
"""

import os
import cohere
import bcrypt
import jwt
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, List, Dict
import re

# Import database
from database.healthbot_db import db

load_dotenv()

app = FastAPI(title="HealthBot AI - Medical Assistant with MongoDB")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key=COHERE_API_KEY) if COHERE_API_KEY else None
print(f"Cohere: {'Connected' if co else 'Not configured'}")

# JWT Secret
SECRET_KEY = os.getenv("JWT_SECRET", "healthbot_secret_key_2024")

# Models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    conversation_id: Optional[str] = None

def is_health_related(message: str) -> bool:
    health_keywords = ["fever", "cold", "cough", "pain", "headache", "stomach", 
                       "symptom", "medicine", "doctor", "health", "sick", "infection"]
    return any(k in message.lower() for k in health_keywords)

def format_with_line_breaks(text: str) -> str:
    pattern = r'(\d+\.)'
    formatted = re.sub(pattern, r'\n\1', text)
    formatted = formatted.lstrip('\n')
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    return formatted

async def generate_response(user_message: str, user_id: str, conversation_id: str = None):
    if not is_health_related(user_message):
        yield "I'm a medical AI assistant. I can only help with health-related questions."
        yield ""
        yield "Please ask about symptoms, conditions, or treatments."
        return
    
    # Create conversation if doesn't exist
    if not conversation_id and db.available:
        conversation_id = db.create_conversation(user_id)
    
    # Get conversation history from MongoDB
    if db.available and conversation_id:
        history = db.get_conversation_history_for_llm(conversation_id, limit=10)
        # Save user message
        db.save_message(conversation_id, user_id, user_message, 'user')
    else:
        history = []
    
    prompt = f"""You are Dr. HealthBot. Provide a CLEAN, WELL-FORMATTED response.

IMPORTANT FORMATTING RULES:
- Start each point on a NEW LINE with a number (1., 2., 3., etc.)
- Put a LINE BREAK after each numbered point
- Keep each point short (1-2 sentences)

Now respond to: {user_message}"""
    
    try:
        response = co.chat(model="command-r-08-2024", message=prompt, temperature=0.7, max_tokens=400)
        answer = response.text.strip()
        formatted_answer = format_with_line_breaks(answer)
        
        # Save bot response to MongoDB
        if db.available and conversation_id:
            db.save_message(conversation_id, user_id, formatted_answer, 'assistant')
        
        # Stream response
        lines = formatted_answer.split('\n')
        for line in lines:
            if line.strip():
                yield line
            else:
                yield ""
            import asyncio
            await asyncio.sleep(0.03)
        
        yield ""
        yield "---"
        yield "💙 Medical AI Assistant | Consult a doctor for serious concerns."
        
    except Exception as e:
        yield f"Error: {str(e)}"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_response(request.message, request.user_id, request.conversation_id),
        media_type="text/plain"
    )

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "cohere_available": co is not None,
        "mongodb_available": db.available
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return db.get_user_activity_stats()

@app.get("/")
async def root():
    return {"message": "HealthBot AI", "status": "running", "database": "MongoDB Atlas"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
