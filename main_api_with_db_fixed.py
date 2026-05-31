# main_api_with_db_fixed.py
"""
HealthBot AI - Fixed Streaming Response
"""

import os
import cohere
import asyncio
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import re

from database.healthbot_db import db

load_dotenv()

app = FastAPI(title="HealthBot AI")

# Enable CORS
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

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    conversation_id: Optional[str] = None

def is_health_related(message: str) -> bool:
    health_keywords = ["fever", "cold", "cough", "pain", "headache", "stomach", 
                       "symptom", "medicine", "doctor", "health", "sick", "infection",
                       "flu", "virus", "nausea", "dizzy", "fatigue", "what is", "how to"]
    return any(k in message.lower() for k in health_keywords)

def format_with_line_breaks(text: str) -> str:
    pattern = r'(\d+\.)'
    formatted = re.sub(pattern, r'\n\1', text)
    formatted = formatted.lstrip('\n')
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    return formatted

async def generate_response(user_message: str, user_id: str, conversation_id: str = None):
    """Generate streaming response"""
    
    # Check if health related
    if not is_health_related(user_message):
        yield "I'm a medical AI assistant. I can only help with health-related questions.\n\n"
        yield "Please ask about symptoms, conditions, or treatments."
        return
    
    # Create conversation in MongoDB if needed
    if not conversation_id and db.available:
        conversation_id = db.create_conversation(user_id)
    
    # Save user message to MongoDB
    if db.available and conversation_id:
        db.save_message(conversation_id, user_id, user_message, 'user')
    
    prompt = f"""You are Dr. HealthBot. Provide a helpful medical response.

User question: {user_message}

Provide a CLEAN response with numbered points if listing information."""

    try:
        # Get response from Cohere
        response = co.chat(
            model="command-r-08-2024", 
            message=prompt, 
            temperature=0.7, 
            max_tokens=400
        )
        answer = response.text.strip()
        formatted_answer = format_with_line_breaks(answer)
        
        # Save bot response to MongoDB
        if db.available and conversation_id:
            db.save_message(conversation_id, user_id, formatted_answer, 'assistant')
        
        # Stream the response line by line
        lines = formatted_answer.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                yield line + "\n"
            else:
                yield "\n"
            await asyncio.sleep(0.05)  # Small delay for streaming effect
        
        # Add footer
        yield "\n---\n💙 Medical AI Assistant | Consult a doctor for serious concerns."
        
    except Exception as e:
        yield f"Error: {str(e)}"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    return StreamingResponse(
        generate_response(request.message, request.user_id, request.conversation_id),
        media_type="text/plain; charset=utf-8"
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
    if db.available:
        return {
            "conversations": db.db.conversations.count_documents({}),
            "messages": db.db.messages.count_documents({}),
            "mongodb": "connected"
        }
    return {"mongodb": "not connected"}

@app.get("/")
async def root():
    return {"message": "HealthBot AI", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
