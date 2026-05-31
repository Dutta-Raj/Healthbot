# standalone_chat_fixed.py
"""Standalone chat server with working /chat endpoint - Fixed version"""

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

app = FastAPI(title="Chatbot API", version="1.0", docs_url="/docs", redoc_url="/redoc")

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
        "message": "Chatbot API is running",
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
    """Process chat messages with medical focus"""
    try:
        print(f"\n[REQUEST] User: {request.user_id}")
        print(f"[MESSAGE] {request.message[:100]}")
        
        message_lower = request.message.lower()
        
        # Comprehensive medical responses
        medical_responses = {
            "blood pressure": "Normal blood pressure is typically around 120/80 mmHg. Here's what the numbers mean:\n• Systolic (top number): 120-129 is normal\n• Diastolic (bottom number): 80-84 is normal\n\nFor personalized advice, please consult your healthcare provider.",
            "bp": "Normal blood pressure is typically around 120/80 mmHg. Here's what the numbers mean:\n• Systolic (top number): 120-129 is normal\n• Diastolic (bottom number): 80-84 is normal\n\nFor personalized advice, please consult your healthcare provider.",
            "headache": "Common causes of headaches include:\n• Dehydration - drink more water\n• Eye strain - take screen breaks\n• Stress - practice relaxation\n• Lack of sleep - maintain regular schedule\n\nIf severe or persistent, consult a doctor.",
            "diabetes": "Key aspects of diabetes management:\n• Monitor blood sugar regularly\n• Follow prescribed medication schedule\n• Maintain healthy diet and exercise\n• Regular check-ups with endocrinologist\n\nAlways follow your doctor's advice.",
            "fever": "Fever management tips:\n• Rest and stay hydrated\n• Use over-the-counter fever reducers\n• Monitor temperature every 4-6 hours\n\nSeek medical attention if:\n• Fever exceeds 103°F (39.4°C)\n• Fever lasts more than 3 days\n• Accompanied by severe symptoms",
            "medication": "Important medication safety tips:\n• Take exactly as prescribed\n• Don't skip doses or double up\n• Check expiration dates\n• Store properly\n• Report side effects to doctor\n\nNever adjust dosage without consulting your healthcare provider.",
            "symptom": "When experiencing symptoms:\n1. Note when they started\n2. Track severity and frequency\n3. Identify triggers\n4. Keep a symptom diary\n\nShare this information with your doctor for better diagnosis.",
            "exercise": "Regular exercise benefits:\n• Improves cardiovascular health\n• Helps maintain healthy weight\n• Reduces stress and anxiety\n• Boosts immune system\n\nAim for 150 minutes of moderate exercise weekly.",
            "diet": "Healthy eating tips:\n• Eat variety of fruits and vegetables\n• Choose whole grains\n• Limit processed foods and sugar\n• Stay hydrated\n• Practice portion control",
            "sleep": "Good sleep hygiene:\n• Maintain consistent sleep schedule\n• Create relaxing bedtime routine\n• Avoid screens before bed\n• Keep bedroom dark and cool\n• Aim for 7-9 hours nightly"
        }
        
        # Check for medical keywords
        response = None
        for keyword, answer in medical_responses.items():
            if keyword in message_lower:
                response = answer
                break
        
        # If no keyword matched, provide a general response
        if not response:
            response = f"I understand you're asking about: '{request.message[:100]}'.\n\nAs a health assistant, I can help with questions about:\n• Blood pressure\n• Headaches and symptoms\n• Diabetes management\n• Fever and medications\n• Exercise and diet\n• Sleep hygiene\n\nCould you please provide more specific details about your health concern?"
        
        # Try to use Cohere for better responses if API key is available
        cohere_api_key = os.getenv('COHERE_API_KEY')
        if cohere_api_key and len(request.message) > 10:
            try:
                import cohere
                co = cohere.Client(cohere_api_key)
                co_response = co.generate(
                    prompt=f"You are a helpful medical assistant. Provide a helpful, accurate response to this health query (keep it informative but not alarmist): {request.message}\n\nResponse:",
                    max_tokens=200,
                    temperature=0.7,
                    stop_sequences=["\n\n"]
                )
                if co_response.generations and co_response.generations[0].text.strip():
                    response = co_response.generations[0].text.strip()
                    print(f"[COHERE] Generated response")
            except Exception as e:
                print(f"[WARN] Cohere error: {e}")
        
        print(f"[RESPONSE] {response[:100]}...")
        
        return ChatResponse(
            response=response,
            user_id=request.user_id,
            session_id=request.session_id or f"session_{int(datetime.now().timestamp())}",
            timestamp=datetime.now().isoformat(),
            status="success"
        )
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test():
    """Test endpoint to verify server is working"""
    return {"message": "Server is working!", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("STANDALONE CHAT SERVER - FIXED VERSION")
    print("="*50)
    print(f"Starting server at: http://localhost:8000")
    print(f"Chat endpoint: POST http://localhost:8000/chat")
    print(f"Health check: GET http://localhost:8000/health")
    print(f"API Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    
    # Run without reload to avoid warning
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
