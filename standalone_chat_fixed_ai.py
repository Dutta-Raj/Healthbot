# standalone_chat_fixed_ai.py
"""Chat server with WORKING Cohere AI"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Chatbot API with AI", version="3.0")

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

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: Optional[str] = None
    timestamp: str
    status: str
    ai_used: bool = False

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat messages with WORKING Cohere AI"""
    try:
        print(f"\n[REQUEST] User: {request.user_id}")
        print(f"[MESSAGE] {request.message[:100]}")
        
        response_text = None
        ai_used = False
        
        # Try Cohere with correct model
        cohere_api_key = os.getenv('COHERE_API_KEY')
        if cohere_api_key and cohere_api_key != 'your_api_key_here':
            try:
                import cohere
                
                # Initialize client
                co = cohere.Client(api_key=cohere_api_key)
                
                # Use the current available model 'command' (not command-r-plus)
                # 'command' is the current stable model as of 2026
                chat_response = co.chat(
                    message=request.message,
                    model="command",  # Current model as of 2026
                    temperature=0.7,
                    max_tokens=300,
                    preamble="You are a helpful medical assistant. Provide accurate, helpful health information. Always recommend consulting healthcare professionals for serious concerns."
                )
                
                if chat_response and chat_response.text:
                    response_text = chat_response.text
                    ai_used = True
                    print("[AI] Cohere 'command' model used successfully")
                    
            except Exception as e:
                print(f"[WARN] Cohere error: {e}")
                print("[INFO] Trying alternative model...")
                
                # Try alternative model 'command-light'
                try:
                    chat_response = co.chat(
                        message=request.message,
                        model="command-light",
                        temperature=0.7,
                        max_tokens=300
                    )
                    if chat_response and chat_response.text:
                        response_text = chat_response.text
                        ai_used = True
                        print("[AI] Cohere 'command-light' model used")
                except Exception as e2:
                    print(f"[WARN] Alternative model also failed: {e2}")
        
        # Fallback to medical responses if AI fails
        if not response_text:
            response_text = get_medical_response(request.message)
            print("[FALLBACK] Using medical response database")
        
        print(f"[RESPONSE] {response_text[:100]}...")
        
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
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "ai_used": False
        }

def get_medical_response(message: str) -> str:
    """Medical response database (fallback)"""
    message_lower = message.lower()
    
    medical_responses = {
        "blood pressure": """Normal blood pressure is typically around 120/80 mmHg.

Blood pressure categories:
• Normal: Less than 120/80 mm Hg
• Elevated: 120-129/less than 80 mm Hg
• High Blood Pressure Stage 1: 130-139/80-89 mm Hg
• Stage 2: 140 and above/90 and above mm Hg

Consult your doctor for personalized advice.""",
        
        "headache": """Common causes of headaches include:
• Dehydration - drink more water
• Eye strain - take screen breaks
• Stress - practice relaxation
• Lack of sleep - maintain regular schedule

See a doctor if headaches are severe or persistent.""",
        
        "diabetes": """Key aspects of diabetes management:
• Monitor blood sugar regularly
• Take medications as prescribed
• Maintain healthy diet and exercise
• Regular check-ups with your doctor""",
        
        "fever": """Fever management:
• Rest and stay hydrated
• Use fever reducers as needed
• Monitor temperature

Seek medical help if fever exceeds 103°F or lasts >3 days.""",
        
        "medication": """Medication safety:
• Take exactly as prescribed
• Don't skip or double doses
• Check expiration dates
• Report side effects to your doctor"""
    }
    
    for keyword, response in medical_responses.items():
        if keyword in message_lower:
            return response
    
    return f"""I understand you're asking about: '{message[:100]}'.

As a health assistant, I can help with questions about:
• Blood pressure and heart health
• Headaches and symptoms
• Diabetes management
• Fever and medications

For serious medical concerns, please consult a healthcare professional."""

if __name__ == "__main__":
    print("\n" + "="*50)
    print("CHATBOT WITH WORKING COHERE AI")
    print("="*50)
    print("Server: http://localhost:8000")
    print("Chat: POST /chat")
    print("Using Cohere 'command' model (current)")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
