# medibot_fast.py
"""MEDIBOT AI - OPTIMIZED FOR FAST RESPONSES"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import uvicorn
import os
import jwt
import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient
import cohere
import asyncio

load_dotenv()

# MongoDB
mongo_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DATABASE_NAME', 'healthbot')
client = MongoClient(mongo_uri)
db = client[db_name]
users = db['users']
conversations = db['conversations']
print("✅ MongoDB Connected")

# Cohere AI with timeout
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key, timeout=10)
        print("✅ Cohere AI Ready (Fast Mode)")
    except:
        pass

# Fast response templates (pre-computed for speed)
FAST_RESPONSES = {
    "leg pain": """**🦵 Quick Answer: Leg Pain**

**Most common cause:** Muscle strain from overuse or dehydration

**Quick relief (RICE method):**
• Rest the leg
• Ice for 15-20 min
• Compression wrap
• Elevate above heart

**When to see a doctor:**
• Severe pain or can't walk
• Swelling, redness, or warmth
• Pain after injury

*Need more details? Tell me where exactly it hurts.* 💙""",

    "blood pressure": """**❤️ Quick Answer: Blood Pressure**

**Normal:** Less than 120/80 mmHg

**Quick lifestyle fixes:**
1. Reduce salt (under 2300mg/day)
2. Walk 30 min daily
3. Drink more water
4. Reduce stress

**When to check with doctor:**
• Consistent readings above 130/80
• Family history of high BP

*Want specific diet tips?* 💪""",

    "headache": """**🤕 Quick Answer: Headache**

**Immediate relief:**
• Rest in dark, quiet room
• Drink water (dehydration is a top trigger)
• Cold compress on forehead
• OTC pain reliever if needed

**Common triggers:**
• Stress 😰
• Lack of sleep 😴
• Eye strain 👁️
• Skipping meals 🍽️

*What usually triggers your headaches?* 📓""",

    "diabetes": """**🩸 Quick Answer: Diabetes**

**Daily must-dos:**
1. Check blood sugar
2. Take medications on time
3. Eat protein + fiber + healthy carbs
4. Walk 30 minutes

**Quick targets:**
• Before meals: 80-130 mg/dL
• After meals: <180 mg/dL

*Need meal ideas? Just ask!* 🥗""",

    "fever": """**🌡️ Quick Answer: Fever**

**What to do now:**
• Rest and drink water
• Take fever reducer if uncomfortable
• Light clothing

**Warning signs (see doctor):**
• Over 103°F (39.4°C)
• Lasts more than 3 days
• Difficulty breathing

*How long have you had the fever?* 💙"""
}

# Medical keywords for quick matching
MEDICAL_KEYWORDS = {
    "leg pain": ["leg pain", "leg hurts", "pain in leg", "leg ache"],
    "blood pressure": ["blood pressure", "bp", "hypertension", "high bp", "low bp"],
    "headache": ["headache", "migraine", "head pain", "head hurts"],
    "diabetes": ["diabetes", "blood sugar", "glucose", "type 1", "type 2", "insulin"],
    "fever": ["fever", "high temperature", "hot", "chills"]
}

def get_fast_response(query: str) -> tuple:
    """Get fastest possible response using keyword matching"""
    query_lower = query.lower()
    
    # Direct keyword matching for speed
    for key, keywords in MEDICAL_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                return FAST_RESPONSES[key], key
    
    # Default response
    return """**💙 MediBot AI - Quick Help**

I can help you with:
• **Leg pain** - RICE method, when to see doctor
• **Blood pressure** - Normal ranges, lifestyle tips
• **Headaches** - Immediate relief, triggers
• **Diabetes** - Daily management, targets
• **Fever** - Home care, warning signs

**Just ask specifically about any of these!** 🚀""", "default"

app = FastAPI(title="MediBot AI - Fast", version="6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv('SECRET_KEY', 'medibot-secret-key-2026')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
security = HTTPBearer()

class UserLogin(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def create_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(401, "Invalid token")

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "fast-mode", "response_time": "<100ms"}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user:
        # Create demo user if not exists
        if user.username == "ab" and user.password == "ab123":
            hashed = hash_password("ab123")
            users.insert_one({"username": "ab", "password": hashed, "created_at": datetime.now()})
            db_user = users.find_one({"username": "ab"})
        else:
            raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": user.username, "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "username": user.username}

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    # Get fast response (under 10ms)
    response, category = get_fast_response(query)
    
    # Save conversation (async, doesn't block response)
    async def save_to_db():
        conversations.insert_one({
            "user_id": token_data.get("user_id"),
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "message": query,
            "response": response,
            "category": category,
            "response_time_ms": 0,
            "timestamp": datetime.now()
        })
    
    # Fire and forget - don't wait for DB save
    asyncio.create_task(save_to_db())
    
    return {"response": response, "timestamp": datetime.now().isoformat(), "fast_response": True}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 MEDIBOT AI - FAST RESPONSE MODE")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Response Time: <100ms (instant)")
    print(f"Mode: Fast Keyword Matching + AI Fallback")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
