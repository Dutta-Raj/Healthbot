# medical_bot_fixed.py
"""MEDICAL CHATBOT WITH FIXED LOGIN"""

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
import re
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

# Cohere
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere Ready")
    except:
        pass

app = FastAPI(title="Medical Chatbot", version="4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv('SECRET_KEY', 'medical-secret-key-2026-make-it-32-chars-long')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
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

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Verify error: {e}")
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
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active" if co else "inactive"}

@app.post("/auth/register")
async def register(user: UserRegister):
    try:
        print(f"\n📝 REGISTER: {user.username}")
        
        existing = users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
        if existing:
            raise HTTPException(400, "Username or email already exists")
        
        hashed_pw = hash_password(user.password)
        user_doc = {
            "username": user.username,
            "email": user.email,
            "password": hashed_pw,
            "full_name": user.full_name,
            "created_at": datetime.now(),
            "role": "user"
        }
        result = users.insert_one(user_doc)
        print(f"  ✅ User created: {user.username}")
        
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
        print(f"  ❌ Error: {e}")
        raise HTTPException(500, str(e))

@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        print(f"\n🔐 LOGIN: '{user.username}' with password length: {len(user.password)}")
        
        # Case-insensitive username search
        db_user = users.find_one({"username": user.username})
        
        if not db_user:
            print(f"  ❌ User not found: {user.username}")
            raise HTTPException(401, "Invalid username or password")
        
        print(f"  ✅ User found: {db_user['username']}")
        print(f"  Stored hash: {db_user['password'][:40]}...")
        
        # Verify password
        is_valid = verify_password(user.password, db_user["password"])
        print(f"  Password match: {is_valid}")
        
        if not is_valid:
            raise HTTPException(401, "Invalid username or password")
        
        token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
        print(f"  ✅ Token created")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(db_user["_id"]),
            "username": db_user["username"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"  ❌ Error: {e}")
        raise HTTPException(500, str(e))

# Medical check
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'migraine', 
    'pain', 'fever', 'cold', 'flu', 'cough', 'symptom', 'medication',
    'doctor', 'hospital', 'health', 'leg pain', 'back pain'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Diabetes\n• Fever"
    else:
        if co:
            try:
                prompt = f"Answer this medical question helpfully: {query}"
                co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=400)
                response = co_response.text if co_response and co_response.text else get_medical_response(query)
            except:
                response = get_medical_response(query)
        else:
            response = get_medical_response(query)
    
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response,
        "timestamp": datetime.now()
    })
    
    return {"response": response, "timestamp": datetime.now().isoformat()}

def get_medical_response(query: str) -> str:
    q = query.lower()
    if "blood pressure" in q:
        return "**Blood Pressure:** Normal is 120/80 mmHg. Prevention: reduce sodium, exercise, maintain healthy weight."
    elif "headache" in q:
        return "**Headache Relief:** Rest, hydrate, use cold compress. See doctor if severe or persistent."
    else:
        return f"I'm a medical assistant. I can help with blood pressure, headaches, diabetes, and fever. Please ask a health question."

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDICAL CHATBOT - FIXED LOGIN")
    print("="*60)
    print("Server: http://localhost:8000")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
