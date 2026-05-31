# medical_rag_restricted.py
"""MEDICAL-ONLY RAG CHATBOT WITH RESTRICTIONS"""

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
    except:
        pass

# Medical keywords for validation
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'cardio', 'diabetes', 'glucose', 'insulin',
    'headache', 'migraine', 'pain', 'fever', 'temperature', 'cold', 'flu', 'cough',
    'symptom', 'treatment', 'medication', 'medicine', 'prescription', 'doctor',
    'hospital', 'clinic', 'emergency', 'health', 'wellness', 'nutrition', 'diet',
    'exercise', 'fitness', 'sleep', 'insomnia', 'anxiety', 'depression', 'stress',
    'allergy', 'asthma', 'infection', 'pregnancy', 'weight', 'obesity', 'cholesterol'
]

NON_MEDICAL_PATTERNS = [
    r'stock|market|crypto|bitcoin|invest',
    r'movie|film|actor|actress|hollywood',
    r'game|gaming|playstation|xbox',
    r'weather|rain|snow|temperature outside',
    r'politics|election|president',
    r'sports|football|cricket|basketball',
    r'reel|instagram|tiktok|facebook|social media',
    r'cooking|recipe|food recipe',
    r'travel|vacation|flight|hotel'
]

def is_medical_query(query: str):
    query_lower = query.lower()
    
    for pattern in NON_MEDICAL_PATTERNS:
        if re.search(pattern, query_lower):
            return False, f"I'm a medical assistant. I can only answer health-related questions. Please ask me about blood pressure, diabetes, headaches, fever, or other medical topics."
    
    for keyword in MEDICAL_KEYWORDS:
        if keyword in query_lower:
            return True, None
    
    return False, "I'm a health-focused assistant. Please ask me medical questions about blood pressure, diabetes, headaches, heart health, or general wellness."

app = FastAPI(title="Medical RAG Chatbot", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv('SECRET_KEY', 'medical-secret-key')
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
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active" if co else "inactive"}

@app.post("/auth/register")
async def register(user: UserRegister):
    if users.find_one({"$or": [{"username": user.username}, {"email": user.email}]}):
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
    db_user = users.find_one({"username": {"$regex": f"^{user.username}$", "$options": "i"}})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid username or password")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "user_id": str(db_user["_id"]), "username": db_user["username"]}

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    user_id = token_data.get("user_id")
    query = request.message
    
    # Check if medical
    is_medical, restriction_msg = is_medical_query(query)
    
    if not is_medical:
        response_text = restriction_msg
    else:
        # Generate medical response
        if co:
            try:
                prompt = f"You are a medical assistant. Answer: {query}\n\nProvide a clear, helpful response. Include disclaimer if needed."
                co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.5, max_tokens=400)
                response_text = co_response.text.strip() if co_response and co_response.text else get_fallback_response(query)
            except:
                response_text = get_fallback_response(query)
        else:
            response_text = get_fallback_response(query)
        
        response_text += "\n\n---\n⚠️ Medical Disclaimer: For educational purposes. Consult a doctor for medical advice."
    
    # Save BOTH user message AND bot response to history
    conversations.insert_one({
        "user_id": user_id,
        "username": token_data.get("sub"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response_text,
        "is_medical": is_medical,
        "timestamp": datetime.now()
    })
    
    return {
        "response": response_text,
        "is_medical": is_medical,
        "timestamp": datetime.now().isoformat()
    }

def get_fallback_response(query: str) -> str:
    q = query.lower()
    if "blood pressure" in q:
        return """**Blood Pressure Guide**

Normal: <120/80 mmHg
Elevated: 120-129/<80
Stage 1: 130-139/80-89
Stage 2: 140+/90+

**Lifestyle changes:**
• Reduce sodium (<2300mg/day)
• Exercise 150 min/week
• Maintain healthy weight"""
    elif "diabetes" in q:
        return """**Diabetes Management**

Targets: Before meals 80-130 mg/dL, After meals <180 mg/dL

Management:
1. Monitor blood sugar
2. Take medications
3. Healthy diet
4. Exercise 150 min/week"""
    elif "headache" in q:
        return """**Headache Relief**

• Rest in dark, quiet room
• Stay hydrated
• Use cold/warm compress
• OTC pain relievers if needed

See doctor if severe or persistent."""
    else:
        return f"""**Health Information**

Regarding your question about "{query[:100]}"

For personalized medical advice, please consult a healthcare professional."""

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    """Get full conversation history including AI responses"""
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history, "count": len(history)}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDICAL RAG CHATBOT")
    print("="*60)
    print("Server: http://localhost:8000")
    print("Medical-Only: YES (rejects non-medical queries)")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
