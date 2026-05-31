import os
import cohere
import bcrypt
import jwt
import random
import urllib.parse
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, List, Dict
import re

load_dotenv()

app = FastAPI(title="HealthBot AI - Medical Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key=COHERE_API_KEY) if COHERE_API_KEY else None
print(f"Cohere: {'Connected' if co else 'Not configured'}")

SECRET_KEY = os.getenv("JWT_SECRET", "healthbot_secret_key_2024")

def create_token(email: str, name: str) -> str:
    payload = {"email": email, "name": name, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    email: str
    name: str
    google_id: str
    picture: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    conversation_id: Optional[str] = None

otp_storage = {}
conversation_history: Dict[str, List[Dict]] = {}

def is_health_related(message: str) -> bool:
    health_keywords = ["fever", "cold", "cough", "pain", "headache", "stomach", "back", "symptom", "medicine", "doctor", "health", "sick", "infection", "allergy", "diabetes", "blood", "heart", "flu", "virus", "nausea", "dizzy", "fatigue", "what is", "how to", "why"]
    return any(k in message.lower() for k in health_keywords)

def format_with_line_breaks(text: str) -> str:
    """Convert numbered list to have line breaks after each number"""
    # Pattern to match numbers like "1.", "2.", "3." etc.
    pattern = r'(\d+\.)'
    
    # Replace each number with newline + number
    formatted = re.sub(pattern, r'\n\1', text)
    
    # Remove leading newline if present
    formatted = formatted.lstrip('\n')
    
    # Ensure spaces between points are clean
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    return formatted

# Auth endpoints (simplified for demo)
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    return {"token": "demo", "user": {"email": req.email, "name": req.name}}

@app.post("/auth/login")
async def login(req: LoginRequest):
    return {"token": "demo", "user": {"email": req.email, "name": "User"}}

@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest):
    return {"token": "demo", "user": {"email": req.email, "name": req.name}}

@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    otp = str(random.randint(100000, 999999))
    print(f"OTP for {req.email}: {otp}")
    return {"message": f"Use OTP: {otp}"}

@app.post("/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    return {"message": "OTP verified"}

@app.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    return {"message": "Password reset"}

async def generate_response(user_message: str, user_id: str, conversation_id: str = None):
    if not is_health_related(user_message):
        yield "I'm a medical AI assistant. I can only help with health-related questions."
        yield ""
        yield "Please ask about symptoms, conditions, or treatments."
        return
    
    if not conversation_id:
        conversation_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    conversation_history[conversation_id].append({"role": "user", "content": user_message})
    recent = conversation_history[conversation_id][-6:]
    
    context = ""
    for msg in recent:
        role = "Patient" if msg["role"] == "user" else "Doctor"
        context += f"{role}: {msg['content']}\n"
    
    prompt = f"""You are Dr. HealthBot. Provide a CLEAN, WELL-FORMATTED response.

IMPORTANT FORMATTING RULES:
- Start each point on a NEW LINE with a number (1., 2., 3., etc.)
- Put a LINE BREAK after each numbered point
- Keep each point short (1-2 sentences)
- Do NOT put multiple numbers on the same line

Example of CORRECT format:

1. Fever is an increase in body temperature.

2. It occurs when your body fights an infection.

3. Normal body temperature is around 98.6°F (37°C).

4. Drink fluids and rest to help recover.

5. See a doctor if fever exceeds 103°F.

Now respond to the patient using this EXACT format:

{context}
Patient: {user_message}

Dr. HealthBot:"""
    
    try:
        response = co.chat(model="command-r-08-2024", message=prompt, temperature=0.7, max_tokens=400)
        answer = response.text.strip()
        
        # Format the response with proper line breaks
        formatted_answer = format_with_line_breaks(answer)
        
        conversation_history[conversation_id].append({"role": "assistant", "content": formatted_answer})
        
        # Stream each line separately
        lines = formatted_answer.split('\n')
        for line in lines:
            if line.strip():
                yield line
            else:
                yield ""  # Preserve empty lines
            import asyncio
            await asyncio.sleep(0.03)
        
        yield ""
        yield "---"
        yield "💙 Medical AI Assistant | Consult a doctor for serious concerns."
        
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
    return {"status": "ok", "cohere_available": co is not None}

@app.get("/")
async def root():
    return {"message": "HealthBot AI", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
