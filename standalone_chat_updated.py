# standalone_chat_updated.py
"""Standalone chat server with updated Cohere Chat API"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Chatbot API", version="2.0", docs_url="/docs", redoc_url="/redoc")

# Add CORS middleware to allow frontend connections
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

@app.get("/")
async def root():
    return {
        "message": "Chatbot API is running with Cohere Chat API",
        "status": "healthy",
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat messages using Cohere Chat API"""
    try:
        print(f"\n[REQUEST] User: {request.user_id}")
        print(f"[MESSAGE] {request.message[:100]}")
        
        response_text = None
        
        # Try to use Cohere Chat API if available
        cohere_api_key = os.getenv('COHERE_API_KEY')
        if cohere_api_key:
            try:
                import cohere
                # Try new ClientV2 first
                try:
                    co = cohere.ClientV2(api_key=cohere_api_key)
                    chat_response = co.chat(
                        model="command-r-plus",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful medical assistant."
                            },
                            {
                                "role": "user",
                                "content": request.message
                            }
                        ],
                        temperature=0.7,
                        max_tokens=300
                    )
                    if chat_response and chat_response.message:
                        response_text = chat_response.message.content[0].text
                        print("[COHERE] Used ClientV2 Chat API")
                except:
                    # Fallback to older client
                    co = cohere.Client(api_key=cohere_api_key)
                    chat_response = co.chat(
                        message=request.message,
                        model="command-r-plus",
                        temperature=0.7
                    )
                    if chat_response and hasattr(chat_response, 'text'):
                        response_text = chat_response.text
                        print("[COHERE] Used legacy Chat API")
            except Exception as e:
                print(f"[WARN] Cohere error: {e}")
        
        # If Cohere didn't work, use local medical responses
        if not response_text:
            response_text = get_medical_response(request.message)
        
        print(f"[RESPONSE] {response_text[:100]}...")
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            session_id=request.session_id or f"session_{int(datetime.now().timestamp())}",
            timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_medical_response(message: str) -> str:
    """Fallback medical responses when Cohere is unavailable"""
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

@app.get("/test")
async def test():
    return {"message": "Server is working!", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("STANDALONE CHAT SERVER - WITH COHERE CHAT API")
    print("="*50)
    print("Server starting at: http://localhost:8000")
    print("Chat endpoint: POST http://localhost:8000/chat")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
