# medibot_with_kafka.py
"""MEDICAL CHATBOT WITH KAFKA - EVENT-DRIVEN ARCHITECTURE"""

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

# Import Kafka module
from kafka_medical_producer import kafka_medical

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
        print("✅ Cohere AI Ready")
    except:
        pass

# Kafka Status
if kafka_medical.enabled:
    print("✅ Kafka Event-Driven Architecture ACTIVE")
    print(f"   📤 Producer: {kafka_medical.bootstrap_servers}")
else:
    print("⚠️ Kafka Disabled - Run start_zookeeper.bat and start_kafka_broker.bat")

# FastAPI App
app = FastAPI(
    title="MediBot AI with Event-Driven Architecture",
    description="Medical Chatbot with Kafka message queuing, RAG, and AI",
    version="5.0"
)
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
    return {
        "status": "healthy",
        "database": "MongoDB Atlas",
        "ai": "active" if co else "inactive",
        "kafka": kafka_medical.enabled,
        "architecture": "Event-Driven with Kafka" if kafka_medical.enabled else "Monolithic"
    }

@app.get("/kafka/status")
async def kafka_status():
    """Endpoint to check Kafka status - for demonstration"""
    return kafka_medical.get_status()

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
    
    # Send registration event to Kafka
    if kafka_medical.enabled:
        kafka_medical.send_analytics({
            "event_type": "user_registered",
            "user_id": str(result.inserted_id),
            "username": user.username
        })
    
    return {"access_token": token, "token_type": "bearer", "user_id": str(result.inserted_id), "username": user.username}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user:
        raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    
    # Send login event to Kafka
    if kafka_medical.enabled:
        kafka_medical.send_analytics({
            "event_type": "user_logged_in",
            "user_id": str(db_user["_id"]),
            "username": db_user["username"]
        })
    
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"]}

# Medical keywords
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'pain', 'fever',
    'leg pain', 'back pain', 'covid', 'anxiety', 'stress', 'symptom'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    user_id = token_data.get("user_id")
    
    # Send chat request to Kafka (for async processing demonstration)
    if kafka_medical.enabled:
        kafka_medical.send_chat_request(user_id, query, request.session_id)
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Leg pain\n• Diabetes\n• Fever"
        return {"response": response, "timestamp": datetime.now().isoformat()}
    
    # Generate response
    if co:
        try:
            prompt = f"You are a medical assistant. Answer: {query}"
            co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=400)
            response = co_response.text if co_response and co_response.text else get_fallback_response(query)
        except:
            response = get_fallback_response(query)
    else:
        response = get_fallback_response(query)
    
    # Send response event to Kafka
    if kafka_medical.enabled:
        kafka_medical.send_analytics({
            "event_type": "chat_completed",
            "user_id": user_id,
            "query_length": len(query),
            "response_length": len(response),
            "is_medical": True
        })
    
    # Save conversation
    conversations.insert_one({
        "user_id": user_id,
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response,
        "kafka_queued": kafka_medical.enabled,
        "timestamp": datetime.now()
    })
    
    return {"response": response, "timestamp": datetime.now().isoformat(), "kafka_used": kafka_medical.enabled}

def get_fallback_response(query: str) -> str:
    q = query.lower()
    if "blood pressure" in q:
        return "**Blood Pressure:** Normal is 120/80 mmHg. Prevention: Reduce sodium, exercise, maintain healthy weight."
    elif "headache" in q:
        return "**Headache Relief:** Rest in dark room, hydrate, cold compress. See doctor if severe."
    elif "leg pain" in q:
        return "**Leg Pain:** Rest, ice, elevation. See doctor if severe or with swelling."
    else:
        return "I'm a medical assistant. I can help with blood pressure, headaches, leg pain, and diabetes."

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "kafka_queued": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDIBOT AI WITH KAFKA EVENT-DRIVEN ARCHITECTURE")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Kafka Status: {'ENABLED ✅' if kafka_medical.enabled else 'DISABLED'}")
    print(f"Architecture: Event-Driven with Message Queue")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
