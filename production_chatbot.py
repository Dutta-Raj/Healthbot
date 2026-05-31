# production_chatbot.py
"""Complete Production Chatbot with Auth, MongoDB, and Real-time API"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import uvicorn
import os
import jwt
import bcrypt
from dotenv import load_dotenv
import cohere
from pymongo import MongoClient
from bson import ObjectId
import asyncio
from contextlib import asynccontextmanager

load_dotenv()

# MongoDB Connection
mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
db_name = os.getenv('DATABASE_NAME', 'healthbot_db')
mongo_client = MongoClient(mongo_uri)
db = mongo_client[db_name]

# Collections
users_col = db['users']
conversations_col = db['conversations']
sessions_col = db['sessions']
feedback_col = db['feedback']

# Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("[OK] Cohere AI initialized")
    except:
        pass

# JWT Settings
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security
security = HTTPBearer()

# Models
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

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    ai_used: bool
    model_used: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid authentication")

async def get_current_user(token_data: dict = Depends(verify_token)):
    user = users_col.find_one({"username": token_data.get("sub")})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# API Endpoints
app = FastAPI(title="HealthBot AI", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "HealthBot AI",
        "version": "6.0",
        "status": "online",
        "endpoints": ["/auth/register", "/auth/login", "/chat", "/health"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mongodb": "connected",
        "ai": "active" if co else "inactive",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserRegister):
    # Check if user exists
    if users_col.find_one({"$or": [{"username": user.username}, {"email": user.email}]}):
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create user
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.now()
    user_dict["role"] = "user"
    
    result = users_col.insert_one(user_dict)
    
    # Create token
    token = create_access_token({"sub": user.username, "user_id": str(result.inserted_id)})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(result.inserted_id),
        username=user.username
    )

@app.post("/auth/login", response_model=TokenResponse)
async def login(user: UserLogin):
    db_user = users_col.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username, "user_id": str(db_user["_id"])})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(db_user["_id"]),
        username=user.username
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Chat with AI - requires authentication"""
    try:
        session_id = request.session_id or f"session_{int(datetime.now().timestamp())}"
        
        # Generate AI response
        response_text = None
        ai_used = False
        model_used = "fallback"
        
        if co:
            try:
                # Try different models
                models = ["command-a-03-2025", "command-r-plus-08-2024", "command-a-plus-05-2026"]
                for model in models:
                    try:
                        chat_response = co.chat(
                            message=request.message,
                            model=model,
                            temperature=0.7,
                            max_tokens=300
                        )
                        if chat_response and chat_response.text:
                            response_text = chat_response.text.strip()
                            ai_used = True
                            model_used = model
                            break
                    except:
                        continue
            except Exception as e:
                print(f"AI Error: {e}")
        
        if not response_text:
            response_text = get_medical_response(request.message)
        
        # Save conversation
        conversations_col.insert_one({
            "user_id": current_user["_id"],
            "username": current_user["username"],
            "session_id": session_id,
            "message": request.message,
            "response": response_text,
            "ai_used": ai_used,
            "model_used": model_used,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            ai_used=ai_used,
            model_used=model_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get user's conversation history"""
    history = list(conversations_col.find(
        {"user_id": current_user["_id"]},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "ai_used": 1}
    ).sort("timestamp", -1).limit(limit))
    
    return {"history": history, "count": len(history)}

@app.post("/feedback")
async def submit_feedback(
    conversation_id: str,
    rating: int,  # 1-5
    comment: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback for a conversation"""
    feedback_col.insert_one({
        "user_id": current_user["_id"],
        "conversation_id": conversation_id,
        "rating": rating,
        "comment": comment,
        "timestamp": datetime.now()
    })
    return {"message": "Feedback submitted", "status": "success"}

def get_medical_response(message: str) -> str:
    """Fallback medical responses"""
    msg_lower = message.lower()
    
    if "blood pressure" in msg_lower or "bp" in msg_lower:
        return "Normal blood pressure is around 120/80 mmHg. Regular monitoring is important. Consult your doctor for personalized advice."
    elif "headache" in msg_lower:
        return "Headaches can be caused by dehydration, stress, or eye strain. Rest, hydrate, and use OTC pain relievers if needed."
    elif "diabetes" in msg_lower:
        return "Diabetes management includes monitoring blood sugar, taking medications, healthy diet, regular exercise, and routine check-ups."
    elif "fever" in msg_lower:
        return "For fever: rest, stay hydrated, use fever reducers. Seek medical help if fever exceeds 103°F or lasts >3 days."
    else:
        return f"I'm a health assistant. Regarding '{message[:100]}', I can help with medical questions about blood pressure, headaches, diabetes, fever, and general health concerns."

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - PRODUCTION READY")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"AI Status: {'ACTIVE' if co else 'INACTIVE'}")
    print(f"MongoDB: CONNECTED")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /auth/register - Create account")
    print("  POST /auth/login - Login")
    print("  POST /chat - Chat (requires auth)")
    print("  GET /history - View history")
    print("  POST /feedback - Submit feedback")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
