# production_chatbot_sqlite.py
"""HealthBot AI with SQLite (No MongoDB required)"""

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
import sqlite3
import json
from dotenv import load_dotenv
import cohere

load_dotenv()

# Initialize SQLite
conn = sqlite3.connect('healthbot.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        role TEXT DEFAULT 'user'
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        session_id TEXT,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        ai_used BOOLEAN DEFAULT 0,
        model_used TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        conversation_id INTEGER,
        rating INTEGER NOT NULL,
        comment TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

conn.commit()
print("✅ SQLite database initialized")

# Initialize Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere AI initialized")
    except:
        pass

# JWT Settings
SECRET_KEY = os.getenv('SECRET_KEY', 'healthbot-secret-key-2026')
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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

app = FastAPI(title="HealthBot AI with SQLite", version="6.1")

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

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "sqlite",
        "ai": "active" if co else "inactive",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserRegister):
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                   (user.username, user.email))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    hashed_password = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, password, full_name) VALUES (?, ?, ?, ?)",
        (user.username, user.email, hashed_password, user.full_name)
    )
    conn.commit()
    user_id = cursor.lastrowid
    
    token = create_access_token({"sub": user.username, "user_id": user_id})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id,
        username=user.username
    )

@app.post("/auth/login", response_model=TokenResponse)
async def login(user: UserLogin):
    cursor.execute("SELECT id, username, password FROM users WHERE username = ?", 
                   (user.username,))
    db_user = cursor.fetchone()
    
    if not db_user or not verify_password(user.password, db_user[2]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username, "user_id": db_user[0]})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=db_user[0],
        username=db_user[1]
    )

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    try:
        user_id = token_data.get("user_id")
        session_id = request.session_id or f"session_{int(datetime.now().timestamp())}"
        
        # Generate AI response
        response_text = None
        ai_used = False
        model_used = "fallback"
        
        if co:
            try:
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
        
        # Save conversation
        cursor.execute(
            "INSERT INTO conversations (user_id, username, session_id, message, response, ai_used, model_used) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, token_data.get("sub"), session_id, request.message, response_text, ai_used, model_used)
        )
        conn.commit()
        
        return {
            "response": response_text,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "ai_used": ai_used,
            "model_used": model_used
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 50, token_data: dict = Depends(verify_token)):
    cursor.execute(
        "SELECT message, response, timestamp, ai_used FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (token_data.get("user_id"), limit)
    )
    history = [{"message": row[0], "response": row[1], "timestamp": row[2], "ai_used": row[3]} 
               for row in cursor.fetchall()]
    return {"history": history, "count": len(history)}

def get_medical_response(message: str) -> str:
    msg_lower = message.lower()
    if "blood pressure" in msg_lower:
        return "Normal blood pressure is around 120/80 mmHg. Regular monitoring is important."
    elif "headache" in msg_lower:
        return "Headaches can be caused by dehydration, stress, or eye strain. Rest and hydrate."
    elif "diabetes" in msg_lower:
        return "Diabetes management includes monitoring blood sugar, healthy diet, and exercise."
    elif "fever" in msg_lower:
        return "For fever: rest, stay hydrated. Seek help if fever exceeds 103°F."
    else:
        return f"I'm a health assistant. Regarding '{message[:100]}', please ask about medical topics."

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - SQLITE VERSION")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Database: SQLite (no MongoDB needed)")
    print(f"AI Status: {'ACTIVE' if co else 'INACTIVE'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
