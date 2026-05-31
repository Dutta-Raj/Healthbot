# medical_bot_complete.py
"""COMPLETE MEDICAL CHATBOT WITH REGISTER ENDPOINT"""

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

app = FastAPI(title="Medical Chatbot", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv('SECRET_KEY', 'medical-secret-key-2026-make-it-long-enough')
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

# Helper functions
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

# Health endpoint
@app.get("/")
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "MongoDB Atlas",
        "ai": "active" if co else "inactive",
        "timestamp": datetime.now().isoformat()
    }

# REGISTER ENDPOINT - ADDED
@app.post("/auth/register")
async def register(user: UserRegister):
    try:
        print(f"\n📝 REGISTER attempt: {user.username}")
        
        # Check if user already exists
        existing = users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
        if existing:
            print(f"  ❌ User already exists: {user.username}")
            raise HTTPException(400, "Username or email already exists")
        
        # Hash password
        hashed_pw = hash_password(user.password)
        print(f"  ✅ Password hashed")
        
        # Create user document
        user_doc = {
            "username": user.username,
            "email": user.email,
            "password": hashed_pw,
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

# LOGIN ENDPOINT
@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        print(f"\n🔐 LOGIN attempt: {user.username}")
        
        # Find user
        db_user = users.find_one({"username": {"$regex": f"^{user.username}$", "$options": "i"}})
        if not db_user:
            print(f"  ❌ User not found: {user.username}")
            raise HTTPException(401, "Invalid username or password")
        
        print(f"  ✅ User found: {db_user['username']}")
        
        # Verify password
        is_valid = verify_password(user.password, db_user["password"])
        print(f"  Password verification: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")
        
        if not is_valid:
            raise HTTPException(401, "Invalid username or password")
        
        # Create token
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
        print(f"  ❌ Login error: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")

# Medical check
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'migraine', 
    'pain', 'fever', 'cold', 'flu', 'cough', 'symptom', 'medication',
    'doctor', 'hospital', 'health', 'leg pain', 'back pain', 'joint pain'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

def get_medical_response(query: str) -> str:
    q = query.lower()
    
    if "blood pressure" in q or "bp" in q:
        return """**Blood Pressure Guide**

Normal: <120/80 mmHg
Elevated: 120-129/<80
Stage 1: 130-139/80-89
Stage 2: 140+/90+

**Lifestyle changes:**
• Reduce sodium (<2300mg/day)
• Exercise 150 min/week
• Maintain healthy weight"""
    
    elif "headache" in q:
        return """**Headache Relief**

• Rest in dark, quiet room
• Stay hydrated
• Use cold/warm compress
• OTC pain relievers if needed

See doctor if severe or persistent."""
    
    elif "diabetes" in q:
        return """**Diabetes Management**

Targets: Before meals 80-130 mg/dL, After meals <180 mg/dL

Management:
1. Monitor blood sugar
2. Take medications
3. Healthy diet
4. Exercise 150 min/week"""
    
    else:
        return f"I'm a medical assistant. I can help with blood pressure, headaches, diabetes, fever, and general health concerns. Could you please rephrase your question?"

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Diabetes\n• Fever\n• Pain management"
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
    
    # Save conversation
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response,
        "timestamp": datetime.now()
    })
    
    return {"response": response, "timestamp": datetime.now().isoformat()}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDICAL CHATBOT - COMPLETE")
    print("="*60)
    print("Server: http://localhost:8000")
    print("Register: POST /auth/register")
    print("Login: POST /auth/login")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
