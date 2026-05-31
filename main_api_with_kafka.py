# main_api_with_kafka.py
"""
HealthBot AI with Kafka Integration
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
import asyncio

from database.healthbot_db import db
from kafka_producer import kafka_producer

load_dotenv()

app = FastAPI(title="HealthBot AI with Kafka")

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
    """Generate streaming response with Kafka integration"""
    
    # Send Kafka event for chat request
    if kafka_producer.enabled:
        kafka_producer.send_chat_request(user_id, user_message, conversation_id or 'new')
    
    if not is_health_related(user_message):
        yield "I can only help with health-related questions."
        return
    
    try:
        response = co.chat(
            model="command-r-08-2024",
            message=f"Medical assistant response to: {user_message}",
            temperature=0.7,
            max_tokens=400
        )
        answer = response.text.strip()
        
        # Send Kafka event for response
        if kafka_producer.enabled:
            kafka_producer.send_chat_response(user_id, answer[:200], conversation_id or 'new')
        
        # Stream response
        yield answer
        
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
        "cohere": co is not None,
        "mongodb": db.available,
        "kafka": kafka_producer.enabled
    }

@app.on_event("startup")
async def startup_event():
    """Start Kafka consumer on startup"""
    # Start Kafka consumer in background
    asyncio.create_task(run_kafka_consumer())

async def run_kafka_consumer():
    from kafka_consumer import kafka_consumer
    kafka_consumer.start_consuming()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
