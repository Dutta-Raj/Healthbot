# healthbot_final.py
"""HEALTHBOT AI - PRODUCTION VERSION WITH MONGODB"""

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

# MongoDB Atlas - Using healthbot database
mongo_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DATABASE_NAME', 'healthbot')
client = MongoClient(mongo_uri)
db = client[db_name]

# Collections
users = db['users']
conversations = db['conversations']
sessions = db['sessions']
feedback = db['feedback']

print("✅ MongoDB Atlas Connected - Database: healthbot")

# Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere AI Ready")
    except Exception as e:
        print(f"⚠️ Cohere init: {e}")

# JWT Settings
SECRET_KEY = os.getenv('SECRET_KEY', 'healthbot-secret')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

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

app = FastAPI(title="HealthBot AI", version="3.0")

# CORS - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(403, "Invalid token")

@app.get("/")
async def root():
    return {
        "name": "HealthBot AI",
        "version": "3.0",
        "database": "MongoDB Atlas - healthbot",
        "status": "online"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "MongoDB Atlas (healthbot)",
        "ai": "active" if co else "inactive",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register")
async def register(user: UserRegister):
    # Check existing
    if users.find_one({"$or": [{"username": user.username}, {"email": user.email}]}):
        raise HTTPException(400, "Username or email already exists")
    
    # Create user
    user_data = {
        "username": user.username,
        "email": user.email,
        "password": hash_password(user.password),
        "full_name": user.full_name,
        "created_at": datetime.now(),
        "role": "user"
    }
    result = users.insert_one(user_data)
    
    token = create_token({"sub": user.username, "user_id": str(result.inserted_id)})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(result.inserted_id),
        "username": user.username
    }

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": user.username, "user_id": str(db_user["_id"])})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(db_user["_id"]),
        "username": user.username
    }

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    try:
        # Generate AI response
        response_text = None
        ai_used = False
        model_used = "fallback"
        
        if co:
            try:
                # Try different models
                models = ["command-a-03-2025", "command-r-plus-08-2024"]
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
        
        # Save to MongoDB
        conversation = {
            "user_id": token_data.get("user_id"),
            "username": token_data.get("sub"),
            "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
            "message": request.message,
            "response": response_text,
            "ai_used": ai_used,
            "model_used": model_used,
            "timestamp": datetime.now()
        }
        conversations.insert_one(conversation)
        
        return {
            "response": response_text,
            "session_id": conversation["session_id"],
            "timestamp": datetime.now().isoformat(),
            "ai_used": ai_used,
            "model_used": model_used
        }
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 50, token_data: dict = Depends(verify_token)):
    try:
        history = list(conversations.find(
            {"user_id": token_data.get("user_id")},
            {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "ai_used": 1}
        ).sort("timestamp", -1).limit(limit))
        
        return {"history": history, "count": len(history)}
    except Exception as e:
        return {"history": [], "count": 0, "error": str(e)}

def get_medical_response(message: str) -> str:
    m = message.lower()
    if "blood pressure" in m or "bp" in m:
        return "Normal blood pressure is 120/80 mmHg. Regular monitoring is important. Consult your doctor for personalized advice."
    elif "headache" in m:
        return "Headaches can be caused by dehydration, stress, or eye strain. Rest, hydrate, and use OTC pain relievers if needed."
    elif "diabetes" in m:
        return "Diabetes management includes monitoring blood sugar, healthy diet, exercise, and taking prescribed medications."
    elif "fever" in m:
        return "For fever: rest, stay hydrated, use fever reducers. Seek help if fever exceeds 103°F or lasts >3 days."
    elif "joke" in m:
        return "Why did the doctor carry a red pen? In case they needed to draw blood! 😊"
    else:
        return f"I'm a health assistant. I can help with medical questions about blood pressure, headaches, diabetes, and fever."

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - PRODUCTION")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Database: MongoDB Atlas - healthbot")
    print(f"AI: {'ACTIVE' if co else 'Fallback Mode'}")
    print(f"Collections: users, conversations, sessions, feedback")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
