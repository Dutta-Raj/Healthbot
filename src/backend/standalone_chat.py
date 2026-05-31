# standalone_chat.py
"""Standalone chat server with /chat endpoint"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Chatbot API", version="1.0")

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: Optional[str] = None
    timestamp: str
    status: str

@app.get("/")
async def root():
    return {"message": "Chatbot API is running", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat messages"""
    try:
        print(f"Received: {request.message[:50]} from user {request.user_id}")
        
        # Simple response logic
        message_lower = request.message.lower()
        
        # Medical responses
        if "blood pressure" in message_lower or "bp" in message_lower:
            response = "Normal blood pressure is typically around 120/80 mmHg. However, please consult your doctor for personalized advice."
        elif "headache" in message_lower:
            response = "Headaches can be caused by various factors including stress, dehydration, or eye strain. If severe or persistent, please consult a healthcare provider."
        elif "diabetes" in message_lower:
            response = "Diabetes management includes monitoring blood sugar, healthy eating, exercise, and medication as prescribed. Please work with your endocrinologist."
        elif "fever" in message_lower:
            response = "For fever, rest and hydration are important. If fever exceeds 103°F (39.4°C) or persists more than 3 days, seek medical attention."
        elif "medication" in message_lower:
            response = "Always take medications as prescribed by your doctor. Never adjust dosage without medical supervision."
        else:
            response = f"I understand you're asking about: '{request.message}'. I'm here to help with health-related questions. Could you provide more details?"
        
        # Try to use Cohere if available
        try:
            import cohere
            cohere_api_key = os.getenv('COHERE_API_KEY')
            if cohere_api_key:
                co = cohere.Client(cohere_api_key)
                co_response = co.generate(
                    prompt=f"As a medical assistant, respond to: {request.message}\nResponse:",
                    max_tokens=100,
                    temperature=0.7
                )
                if co_response.generations:
                    response = co_response.generations[0].text.strip()
        except:
            pass
        
        return ChatResponse(
            response=response,
            user_id=request.user_id,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docs")
async def get_docs():
    return {"message": "API documentation available at /redoc"}

if __name__ == "__main__":
    print("Starting Standalone Chat Server...")
    print("Chat endpoint: http://localhost:8000/chat")
    print("Health check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
