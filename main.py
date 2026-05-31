# main.py - Complete Medical Chatbot with Frontend Serving
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from pymongo import MongoClient
import cohere
import uvicorn

# Load environment variables
load_dotenv("config/.env")

# MongoDB Connection
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

# JWT Settings
SECRET_KEY = os.getenv('SECRET_KEY', 'medibot-secret-key-2026')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
security = HTTPBearer()

# Pydantic Models
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

# Helper Functions
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
    medical_keywords = [
        'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'pain',
        'fever', 'cold', 'flu', 'cough', 'symptom', 'medication', 'doctor',
        'hospital', 'health', 'leg pain', 'back pain', 'stomach', 'nausea',
        'dizzy', 'fatigue', 'sleep', 'anxiety', 'depression', 'stress',
        'allergy', 'asthma', 'infection', 'cancer', 'pregnancy', 'baby',
        'weight', 'cholesterol', 'stroke', 'cut', 'bleed', 'burn', 'broken'
    ]
    return any(kw in query.lower() for kw in medical_keywords)

async def get_conversation_history(session_id: str, limit: int = 5):
    history = list(conversations_collection.find(
        {"session_id": session_id},
        {"_id": 0, "message": 1, "response": 1}
    ).sort("timestamp", -1).limit(limit))
    history.reverse()
    return history

async function generate_response(query: str, session_id: str = None) -> str:
    if not is_medical_query(query):
        return "💙 I'm a MEDICAL assistant. Please ask me health-related questions."
    
    if not co:
        return get_fallback_response(query)
    
    try:
        context = ""
        if session_id:
            history = await get_conversation_history(session_id, limit=3)
            if history:
                context = "Previous conversation:\n"
                for h in history:
                    context += f"User: {h['message']}\nAssistant: {h['response']}\n"
        
        prompt = f"""You are MediBot AI, a compassionate medical assistant.

{context}
User: {query}

Provide a helpful, accurate response. Use bullet points. End with a follow-up question."""
        
        response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=500)
        return response.text.strip() if response and response.text else get_fallback_response(query)
    except:
        return get_fallback_response(query)

def get_fallback_response(query: str) -> str:
    q = query.lower()
    if "blood pressure" in q:
        return "**Blood Pressure:** Normal is 120/80 mmHg. Prevention: Reduce salt, exercise."
    elif "headache" in q:
        return "**Headache Relief:** Rest in dark room, hydrate, cold compress."
    elif "diabetes" in q:
        return "**Diabetes Management:** Monitor blood sugar, healthy diet, exercise."
    else:
        return "I'm here to help with medical questions. Please consult a healthcare professional."

# FastAPI App
app = FastAPI(title="MediBot AI", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Serve Frontend Files
frontend_path = os.path.join(os.path.dirname(__file__), "src/frontend")
if os.path.exists(frontend_path):
    # Mount static files
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    # Serve frontend at root
    @app.get("/")
    async def serve_frontend():
        index_file = os.path.join(frontend_path, "frontend_complete.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend not found", "status": "error"}

# API Endpoints
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
    response = await generate_response(request.message, session_id)
    
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
    print("🏥 MEDIBOT AI - INTELLIGENT MEDICAL ASSISTANT")
    print("="*60)
    print("Server: http://localhost:8000")
    print("Frontend: http://localhost:8000/")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
