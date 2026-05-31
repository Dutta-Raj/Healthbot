# healthbot_fixed_auth.py
"""HEALTHBOT AI - FIXED AUTHENTICATION"""

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
from bson import ObjectId
import cohere

load_dotenv()

# MongoDB Atlas
mongo_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DATABASE_NAME', 'healthbot')
client = MongoClient(mongo_uri)
db = client[db_name]

users = db['users']
conversations = db['conversations']

print("✅ MongoDB Atlas Connected")

# Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere AI Ready")
    except Exception as e:
        print(f"⚠️ Cohere init: {e}")

# Use a proper 32-byte secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'healthbot-secret-key-2026-must-be-32-chars')
if len(SECRET_KEY) < 32:
    SECRET_KEY = SECRET_KEY + "x" * (32 - len(SECRET_KEY))
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

app = FastAPI(title="HealthBot AI", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash with proper error handling"""
    try:
        if not hashed or not password:
            return False
        result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        return result
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def create_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "MongoDB Atlas",
        "ai": "active" if co else "inactive",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register")
async def register(user: UserRegister):
    try:
        print(f"\n📝 REGISTER: {user.username}")
        
        # Check if user exists
        existing_user = users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
        if existing_user:
            print(f"  ❌ User already exists")
            raise HTTPException(400, "Username or email already exists")
        
        # Hash password
        hashed_password = hash_password(user.password)
        print(f"  ✅ Password hashed: {hashed_password[:30]}...")
        
        # Create user document
        user_doc = {
            "username": user.username,
            "email": user.email,
            "password": hashed_password,
            "full_name": user.full_name,
            "created_at": datetime.now(),
            "role": "user"
        }
        
        result = users.insert_one(user_doc)
        print(f"  ✅ User created with ID: {result.inserted_id}")
        
        # Create access token
        token = create_token({"sub": user.username, "user_id": str(result.inserted_id)})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(result.inserted_id),
            "username": user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"  ❌ Registration error: {e}")
        raise HTTPException(500, f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        print(f"\n🔐 LOGIN attempt: {user.username}")
        
        # Find user by username (case-insensitive)
        db_user = users.find_one({"username": {"$regex": f"^{user.username}$", "$options": "i"}})
        
        if not db_user:
            print(f"  ❌ User not found: {user.username}")
            raise HTTPException(401, "Invalid username or password")
        
        print(f"  ✅ User found: {db_user['username']}")
        print(f"  Stored hash: {db_user['password'][:30]}...")
        
        # Verify password
        is_valid = verify_password(user.password, db_user["password"])
        print(f"  Password verification: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")
        
        if not is_valid:
            raise HTTPException(401, "Invalid username or password")
        
        # Create token
        token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
        print(f"  ✅ Token created successfully")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(db_user["_id"]),
            "username": db_user["username"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"  ❌ Login error: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    try:
        print(f"\n💬 CHAT: {token_data.get('sub')} -> {request.message[:50]}...")
        
        response_text = None
        
        if co:
            try:
                chat_response = co.chat(
                    message=request.message,
                    model="command-a-03-2025",
                    temperature=0.7,
                    max_tokens=300
                )
                if chat_response and chat_response.text:
                    response_text = chat_response.text.strip()
                    print(f"  ✅ AI response generated")
            except Exception as e:
                print(f"  ⚠️ AI error: {e}")
        
        if not response_text:
            response_text = get_fallback_response(request.message)
        
        # Save conversation
        conversation = {
            "user_id": token_data.get("user_id"),
            "username": token_data.get("sub"),
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "message": request.message,
            "response": response_text,
            "timestamp": datetime.now()
        }
        conversations.insert_one(conversation)
        print(f"  ✅ Conversation saved")
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat(),
            "ai_used": bool(co)
        }
        
    except Exception as e:
        print(f"  ❌ Chat error: {e}")
        raise HTTPException(500, str(e))

def get_fallback_response(message: str) -> str:
    msg_lower = message.lower()
    if "blood pressure" in msg_lower:
        return "Normal blood pressure is typically 120/80 mmHg. Consult your doctor for personalized advice."
    elif "headache" in msg_lower:
        return "Headaches can be caused by dehydration, stress, or eye strain. Rest and hydrate."
    elif "diabetes" in msg_lower:
        return "Diabetes management includes monitoring blood sugar, healthy diet, and exercise."
    elif "fever" in msg_lower:
        return "For fever: rest, stay hydrated. Seek help if fever exceeds 103°F."
    else:
        return f"I'm a health assistant. Regarding '{message[:100]}', I can help with medical questions."

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - FIXED AUTHENTICATION")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Database: MongoDB Atlas - healthbot")
    print(f"AI: {'ACTIVE' if co else 'INACTIVE'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
