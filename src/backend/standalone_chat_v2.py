# standalone_chat_v2.py
"""Chatbot with WORKING Cohere AI - Corrected Version"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="Chatbot API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat messages with Cohere AI"""
    try:
        print(f"\n[REQUEST] {request.user_id}: {request.message[:50]}")
        
        response_text = None
        ai_used = False
        
        # Cohere API configuration
        api_key = os.getenv('COHERE_API_KEY')
        
        if api_key and api_key != 'your_api_key_here':
            try:
                # Use Cohere API directly via REST (more reliable)
                url = "https://api.cohere.ai/v1/chat"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "message": request.message,
                    "model": "command",  # Stable model
                    "temperature": 0.7,
                    "max_tokens": 300,
                    "preamble": "You are a helpful assistant. Provide clear, accurate responses."
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('text', data.get('message', {}).get('content', ''))
                    if response_text:
                        ai_used = True
                        print(f"[AI] Cohere response: {response_text[:50]}...")
                else:
                    print(f"[WARN] Cohere API error: {response.status_code} - {response.text[:100]}")
                    
            except Exception as e:
                print(f"[WARN] Cohere error: {e}")
        
        # Fallback response
        if not response_text:
            response_text = get_fallback_response(request.message)
            print("[FALLBACK] Using local response")
        
        return {
            "response": response_text,
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "ai_used": ai_used
        }
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return {
            "response": "I apologize, but I encountered an error. Please try again.",
            "user_id": request.user_id,
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "ai_used": False
        }

def get_fallback_response(message: str) -> str:
    """Fallback responses"""
    message_lower = message.lower()
    
    # Medical responses
    if "blood pressure" in message_lower:
        return "Normal blood pressure is around 120/80 mmHg. Consult your doctor for personalized advice."
    elif "headache" in message_lower:
        return "Headaches can be caused by dehydration, stress, or eye strain. Rest and hydration may help."
    elif "diabetes" in message_lower:
        return "Diabetes management includes monitoring blood sugar, healthy diet, exercise, and prescribed medications."
    elif "fever" in message_lower:
        return "For fever, rest and stay hydrated. Seek medical help if fever exceeds 103°F."
    elif "joke" in message_lower:
        return "Why don't scientists trust atoms? Because they make up everything!"
    elif "capital" in message_lower:
        return "I'm a medical assistant focused on health questions. For general knowledge, please consult a search engine."
    else:
        return f"I understand you're asking about: '{message[:100]}'. I specialize in health and medical questions. Could you please rephrase your question?"

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("CHATBOT V2 - WITH COHERE API")
    print("="*50)
    print(f"Server: http://localhost:8000")
    print(f"Chat: POST /chat")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
