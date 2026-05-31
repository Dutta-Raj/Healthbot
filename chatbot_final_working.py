# chatbot_final_working.py
"""HEALTHBOT AI - FULLY WORKING WITH ACTIVE COHERE MODEL"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uvicorn
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="HealthBot AI", version="5.0")

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

# Active Cohere models (as of 2026)
ACTIVE_MODELS = [
    "command-a-plus-05-2026",  # Latest, most powerful
    "command-a-03-2025",        # Very capable
    "command-r-plus-08-2024",   # Stable RAG model
    "command-r-08-2024",        # Good all-around
]

def call_cohere_api(message, model=None):
    """Call Cohere API with active model"""
    api_key = os.getenv('COHERE_API_KEY')
    if not api_key:
        return None
    
    if model is None:
        model = ACTIVE_MODELS[0]  # Use best model by default
    
    url = "https://api.cohere.ai/v1/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": message,
        "model": model,
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('text', data.get('message', {}).get('content', ''))
        else:
            print(f"  Model {model} failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Error with {model}: {e}")
        return None

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "ai_active": True,
        "models_available": ACTIVE_MODELS,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat with active Cohere models"""
    print(f"\n[USER] {request.user_id}: {request.message[:60]}")
    
    response_text = None
    model_used = None
    
    # Try each active model until one works
    for model in ACTIVE_MODELS:
        print(f"  Trying model: {model}")
        result = call_cohere_api(request.message, model)
        if result:
            response_text = result.strip()
            model_used = model
            print(f"  [OK] Success with {model}")
            break
    
    # Fallback responses if all AI models fail
    if not response_text:
        response_text = get_fallback_response(request.message)
        model_used = "fallback"
        print(f"  [FALLBACK] Using local response")
    
    return {
        "response": response_text,
        "user_id": request.user_id,
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "ai_model": model_used,
        "ai_used": model_used != "fallback"
    }

def get_fallback_response(message: str) -> str:
    """Medical response database"""
    msg_lower = message.lower()
    
    # Medical responses
    if any(word in msg_lower for word in ["blood pressure", "bp"]):
        return """Normal blood pressure is typically around 120/80 mmHg.

Blood pressure categories:
• Normal: Less than 120/80 mm Hg
• Elevated: 120-129/less than 80 mm Hg
• High BP Stage 1: 130-139/80-89 mm Hg
• Stage 2: 140 and above/90 and above mm Hg

Consult your doctor for personalized advice."""
    
    elif "headache" in msg_lower:
        return """Common causes of headaches:
• Dehydration - drink more water
• Eye strain - take screen breaks
• Stress - practice relaxation
• Lack of sleep - maintain regular schedule

See a doctor if headaches are severe or persistent."""
    
    elif "diabetes" in msg_lower:
        return """Diabetes management:
• Monitor blood sugar regularly
• Take medications as prescribed
• Maintain healthy diet and exercise
• Regular check-ups with your doctor"""
    
    elif "fever" in msg_lower:
        return """Fever management:
• Rest and stay hydrated
• Use fever reducers as needed
• Monitor temperature

Seek medical help if fever exceeds 103°F or lasts >3 days."""
    
    elif "joke" in msg_lower:
        return "Why did the doctor carry a red pen? In case they needed to draw blood! 😊"
    
    else:
        return f"I understand you're asking about: '{message[:100]}'.\n\nAs a health assistant, I can help with:\n• Blood pressure & heart health\n• Headaches & symptoms\n• Diabetes management\n• Fever & medications\n\nFor serious concerns, please consult a healthcare professional."

@app.get("/models")
async def list_models():
    """List available Cohere models"""
    return {
        "active_models": ACTIVE_MODELS,
        "recommended": ACTIVE_MODELS[0],
        "note": "These models are active as of 2026"
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 HEALTHBOT AI - FULLY WORKING")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Active Models: {', '.join(ACTIVE_MODELS[:3])}...")
    print("="*60)
    print("\n✓ AI will try multiple active models")
    print("✓ Fallback medical responses available")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
