# main_api_with_queue.py
"""
HealthBot AI with In-Memory Message Queue
No external dependencies!
"""

import os
import cohere
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import re

from database.healthbot_db import db
from simple_kafka import message_bus

load_dotenv()

app = FastAPI(title="HealthBot AI with Message Queue")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key=COHERE_API_KEY) if COHERE_API_KEY else None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    conversation_id: Optional[str] = None

def is_health_related(message: str) -> bool:
    health_keywords = ["fever", "cold", "cough", "pain", "headache", "symptom", 
                       "medicine", "doctor", "health", "sick", "infection"]
    return any(k in message.lower() for k in health_keywords)

async def generate_response(user_message: str, user_id: str, conversation_id: str = None):
    """Generate streaming response with queue integration"""
    
    # Send to message queue
    message_bus.send_chat_request(user_id, user_message, conversation_id or 'new')
    message_bus.send_medical_query(user_id, user_message, {'conversation_id': conversation_id})
    
    if not is_health_related(user_message):
        response = "I can only help with health-related questions. Please ask about symptoms, conditions, or treatments."
        yield response
        return
    
    try:
        response = co.chat(
            model="command-r-08-2024",
            message=f"You are Dr. HealthBot. Respond to this medical question: {user_message}",
            temperature=0.7,
            max_tokens=400
        )
        answer = response.text.strip()
        
        # Send response to queue
        message_bus.send_chat_response(user_id, answer, conversation_id or 'new')
        
        # Stream response
        yield answer
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield error_msg

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
        "cohere": co is not None,
        "mongodb": db.available,
        "message_queue": message_bus.enabled
    }

@app.get("/queue/stats")
async def queue_stats():
    """Get message queue statistics"""
    return message_bus.get_stats()

@app.get("/queue/messages/{topic}")
async def get_queue_messages(topic: str, limit: int = 50):
    """Get recent messages from a topic"""
    topics_map = {
        'requests': 'healthbot.chat.requests',
        'responses': 'healthbot.chat.responses',
        'feedback': 'healthbot.user.feedback',
        'queries': 'healthbot.medical.queries',
        'analytics': 'healthbot.analytics.events'
    }
    
    topic_name = topics_map.get(topic)
    if not topic_name:
        return {"error": "Invalid topic"}
    
    return {"messages": message_bus.queue.get_messages(topic_name, limit)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
