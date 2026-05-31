# main.py - Medical Chatbot with PROPER Conversation Memory
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient
import cohere
import uvicorn

load_dotenv()

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'healthbot')
client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
users_collection = db['users']
conversations_collection = db['conversations']
print("✅ MongoDB Connected")

# Cohere AI
COHERE_API_KEY = os.getenv('COHERE_API_KEY')
co = None
if COHERE_API_KEY:
    try:
        co = cohere.Client(api_key=COHERE_API_KEY)
        print("✅ Cohere AI Ready")
    except Exception as e:
        print(f"⚠️ Cohere error: {e}")

SECRET_KEY = os.getenv('SECRET_KEY', 'medibot-secret-key-2026')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
security = HTTPBearer()

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

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

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(401, "Invalid token")

def is_medical_query(query: str) -> bool:
    """Check if query is health-related"""
    medical_keywords = [
        'pain', 'leg', 'arm', 'head', 'stomach', 'back', 'chest',
        'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 
        'fever', 'cold', 'flu', 'cough', 'symptom', 'medication',
        'doctor', 'hospital', 'health', 'nausea', 'dizzy', 'fatigue',
        'sleep', 'anxiety', 'stress', 'allergy', 'infection'
    ]
    q = query.lower()
    return any(kw in q for kw in medical_keywords) or len(query) < 10

def get_conversation_history(session_id: str, limit: int = 10):
    """Get full conversation history for context"""
    history = list(conversations_collection.find(
        {"session_id": session_id},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1).limit(limit))
    return history

def generate_response_with_memory(query: str, session_id: str = None) -> str:
    """Generate response with full conversation memory"""
    
    # Get conversation history
    history = []
    if session_id:
        history = get_conversation_history(session_id, limit=10)
    
    # Build conversation context
    context = ""
    if history:
        context = "Previous conversation:\n"
        for h in history[-8:]:  # Last 8 exchanges for context
            context += f"User: {h['message']}\nAssistant: {h['response']}\n"
        context += f"\nUser just said: {query}\n"
    
    if not co:
        return get_smart_fallback(query, history)
    
    try:
        if context:
            prompt = f"""You are MediBot AI, a warm, helpful medical assistant. Continue this conversation naturally.

{context}

Instructions:
- DO NOT start over - continue the conversation
- Reference what the user said earlier
- Answer directly without repeating previous information
- Be conversational and helpful
- Ask a relevant follow-up question

Your response:"""
        else:
            prompt = f"""You are MediBot AI, a warm, helpful medical assistant.

User: {query}

Provide a helpful, accurate response. Be conversational. End with a follow-up question.

Response:"""
        
        response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=500)
        return response.text.strip() if response and response.text else get_smart_fallback(query, history)
    except Exception as e:
        print(f"Cohere error: {e}")
        return get_smart_fallback(query, history)

def get_smart_fallback(query: str, history: List[Dict]) -> str:
    """Smart fallback that understands context"""
    q = query.lower()
    
    # Check if this is a follow-up answer
    if history and len(history) > 0:
        last_user_msg = history[-1]['message'].lower()
        
        # Leg pain follow-up
        if 'leg pain' in last_user_msg or 'leg' in last_user_msg:
            if '4 days' in q or 'day' in q or 'week' in q:
                return """Thanks for letting me know it's been 4 days. That's helpful information.

**Since you've had leg pain for 4 days, here's what I recommend:**

1. **Rest** - Avoid strenuous activity on that leg
2. **Ice** - Apply ice for 15-20 minutes, 3-4 times daily
3. **Elevate** - Keep leg raised when sitting/lying down
4. **OTC pain reliever** - Ibuprofen or acetaminophen may help

**You should see a doctor if:**
• Pain gets worse
• You can't walk normally
• Swelling or redness appears
• Pain doesn't improve in a few more days

*Did this pain start after an injury or specific activity?* 💙"""
            
            elif 'no' in q:
                return """Thanks for confirming no swelling or numbness. That's good news - it suggests the pain may be muscular rather than nerve-related.

**Try these for the next 2-3 days:**
• Rest the leg
• Ice for 15-20 minutes, 3x daily
• Gentle stretching if it feels tight
• Over-the-counter pain reliever

*On a scale of 1-10, how would you rate the pain?* 💙"""
            
            elif 'yes' in q:
                return """I see. Since you have swelling or numbness with the leg pain, that's more concerning.

**I recommend seeing a doctor soon because:**
• Swelling + pain could indicate a strain or inflammation
• Numbness might suggest nerve involvement

**In the meantime:**
• Keep the leg elevated
• Apply ice if there's swelling
• Avoid putting too much weight on it

*Have you had any injury or started new exercise recently?* 💙"""
    
    # Default responses
    if 'leg pain' in q:
        return """I'm sorry to hear about your leg pain. Let me help you figure this out.

**To give you the best advice, could you tell me:**
• How long have you had the pain?
• Is it sharp, dull, or throbbing?
• Any swelling, redness, or numbness?
• Did it start after an injury or activity?

This will help me understand what might be going on! 💙"""
    
    elif 'blood pressure' in q:
        return "**Blood Pressure Guide**\n\nNormal: <120/80\nElevated: 120-129/<80\nStage 1: 130-139/80-89\nStage 2: 140+/90+\n\n*Have you been monitoring your BP at home?*"
    
    elif 'headache' in q:
        return "**Headache Relief**\n\n• Rest in dark, quiet room\n• Stay hydrated\n• Cold compress on forehead\n\n*What usually triggers your headaches?*"
    
    else:
        return f"I'm here to help with health questions. Could you tell me more about '{query[:50]}'?"

app = FastAPI(title="MediBot AI", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Frontend not found"}

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active" if co else "inactive"}

@app.post("/auth/register")
async def register(user: UserRegister):
    if users_collection.find_one({"$or": [{"username": user.username}, {"email": user.email}]}):
        raise HTTPException(400, "Username or email already exists")
    
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": hash_password(user.password),
        "full_name": user.full_name,
        "created_at": datetime.now()
    }
    result = users_collection.insert_one(user_doc)
    token = create_token({"sub": user.username, "user_id": str(result.inserted_id)})
    return {"access_token": token, "token_type": "bearer", "username": user.username}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users_collection.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"]}

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    session_id = request.session_id or f"session_{int(datetime.now().timestamp())}"
    response = generate_response_with_memory(request.message, session_id)
    
    conversations_collection.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": session_id,
        "message": request.message,
        "response": response,
        "timestamp": datetime.now()
    })
    
    return {"response": response, "session_id": session_id, "timestamp": datetime.now().isoformat()}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations_collection.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDIBOT AI - WITH PROPER MEMORY")
    print("="*60)
    print("Server: http://localhost:10000")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=10000)
