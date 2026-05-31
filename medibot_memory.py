# medibot_memory.py
"""MEDIBOT AI - WITH CONVERSATION MEMORY & FOLLOW-UP QUESTIONS"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uvicorn
import os
import jwt
import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient
import cohere

load_dotenv()

# MongoDB
mongo_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DATABASE_NAME', 'healthbot')
client = MongoClient(mongo_uri)
db = client[db_name]
users = db['users']
conversations = db['conversations']
print("✅ MongoDB Connected")

# Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere AI Ready (With Conversation Memory)")
    except:
        pass

app = FastAPI(title="MediBot AI - With Memory", version="10.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(401, "Invalid token")

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active", "memory": "enabled"}

@app.post("/auth/register")
async def register(user: UserRegister):
    existing = users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing:
        raise HTTPException(400, "Username or email already exists")
    
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": hash_password(user.password),
        "full_name": user.full_name,
        "created_at": datetime.now()
    }
    result = users.insert_one(user_doc)
    token = create_token({"sub": user.username, "user_id": str(result.inserted_id)})
    return {"access_token": token, "token_type": "bearer", "user_id": str(result.inserted_id), "username": user.username}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user:
        raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"]}

async def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict]:
    """Get recent conversation history for context"""
    history = list(conversations.find(
        {"session_id": session_id},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(limit))
    
    # Reverse to get chronological order
    history.reverse()
    return history

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    user_id = token_data.get("user_id")
    session_id = request.session_id or f"session_{int(datetime.now().timestamp())}"
    
    # Get conversation history for context (for follow-up questions)
    history = await get_conversation_history(session_id, limit=5)
    
    # Build conversation context for AI
    context = ""
    if history:
        context = "\nPrevious conversation:\n"
        for h in history[-3:]:  # Last 3 exchanges for context
            context += f"User: {h['message']}\nAssistant: {h['response']}\n"
        context += f"\nCurrent question: {query}\n"
    
    if co:
        try:
            if context:
                prompt = f"""You are MediBot AI, a helpful medical assistant. Use the conversation history to answer follow-up questions naturally.

{context}

Instructions:
- If this is a follow-up question, refer to previous answers
- Be conversational and helpful
- Provide accurate medical information
- Ask clarifying questions if needed
- End with a helpful follow-up question

Response:"""
            else:
                prompt = f"""You are MediBot AI, a helpful medical assistant. Answer this health question naturally and conversationally.

Question: {query}

Instructions:
- Be warm and helpful
- Provide accurate information
- Ask a follow-up question to better help the user

Response:"""
            
            response = co.chat(
                message=prompt,
                model="command-a-03-2025",
                temperature=0.7,
                max_tokens=500
            )
            
            response_text = response.text.strip() if response and response.text else "I'm here to help with your medical questions. Could you provide more details?"
            
        except Exception as e:
            print(f"AI error: {e}")
            response_text = f"I'm here to help with your medical question. Could you please provide more details about '{query[:100]}'?"
    else:
        response_text = f"I'm here to help with medical questions. Regarding '{query[:100]}', could you tell me more?"
    
    # Save conversation
    conversations.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "message": query,
        "response": response_text,
        "timestamp": datetime.now()
    })
    
    return {"response": response_text, "session_id": session_id, "timestamp": datetime.now().isoformat()}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧠 MEDIBOT AI - WITH CONVERSATION MEMORY")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Memory: ENABLED (remembers conversation context)")
    print(f"Follow-up Questions: SUPPORTED")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
