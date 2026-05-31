# chatbot_final.py
"""FULLY WORKING CHATBOT with Cohere AI"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv
import cohere

load_dotenv()

app = FastAPI(title="HealthBot AI", version="4.0")

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

# Initialize Cohere with working model
api_key = os.getenv('COHERE_API_KEY')
co = None
working_model = None

if api_key and api_key != 'your_api_key_here':
    try:
        co = cohere.Client(api_key=api_key)
        working_model = "command-nightly"  # The working model from tests
        print(f"[OK] Cohere initialized with model: {working_model}")
    except Exception as e:
        print(f"[WARN] Cohere init error: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat messages with WORKING Cohere AI"""
    try:
        print(f"\n[USER] {request.user_id}")
        print(f"[MSG] {request.message[:80]}")
        
        response_text = None
        ai_used = False
        
        # Try Cohere AI first
        if co:
            try:
                # Use the working model
                chat_response = co.chat(
                    message=request.message,
                    model=working_model,  # command-nightly works!
                    temperature=0.7,
                    max_tokens=300,
                    preamble="You are a helpful medical assistant. Provide accurate, helpful information. For medical advice, always recommend consulting healthcare professionals."
                )
                
                if chat_response and chat_response.text:
                    response_text = chat_response.text.strip()
                    ai_used = True
                    print(f"[AI] Cohere response generated")
                    
            except Exception as e:
                print(f"[WARN] Cohere error: {e}")
        
        # Fallback to medical responses if AI fails
        if not response_text:
            response_text = get_medical_response(request.message)
            print("[FALLBACK] Using medical database")
        
        print(f"[RESPONSE] {response_text[:100]}...")
        
        return {
            "response": response_text,
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "ai_used": ai_used,
            "model": working_model if ai_used else "fallback"
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

def get_medical_response(message: str) -> str:
    """Medical response database"""
    msg_lower = message.lower()
    
    responses = {
        "blood pressure": "Normal blood pressure is around 120/80 mmHg. Regular monitoring is important. Consult your doctor for personalized advice.",
        "headache": "Common headache causes: dehydration, stress, eye strain, lack of sleep. Rest, hydrate, and use OTC pain relievers if needed.",
        "diabetes": "Diabetes management: monitor blood sugar, take medications, healthy diet, regular exercise, and routine check-ups.",
        "fever": "For fever: rest, stay hydrated, use fever reducers. Seek help if fever exceeds 103°F or lasts >3 days.",
        "joke": "Why did the doctor carry a red pen? In case they needed to draw blood! 😊",
        "capital": "I specialize in health questions. For general knowledge like capitals, please ask me about medical topics!"
    }
    
    for key, response in responses.items():
        if key in msg_lower:
            return response
    
    return f"I understand you're asking: '{message[:100]}'. I'm a health assistant focused on medical questions. Could you please ask about health topics like blood pressure, headaches, or diabetes?"

@app.get("/info")
async def info():
    return {
        "name": "HealthBot AI",
        "version": "4.0",
        "ai_model": working_model if co else "None",
        "ai_status": "active" if co else "inactive",
        "endpoints": ["/chat", "/health", "/info"]
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 HEALTHBOT AI - FULLY WORKING")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"AI Model: {working_model if co else 'Fallback Mode'}")
    print(f"Status: {'AI ACTIVE' if co else 'Fallback Active'}")
    print("="*60)
    print("\n✓ Chat endpoint: POST /chat")
    print("✓ Health check: GET /health")
    print("✓ API info: GET /info")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
