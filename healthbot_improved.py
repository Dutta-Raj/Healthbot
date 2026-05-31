# healthbot_improved.py
"""HEALTHBOT AI WITH IMPROVED RESPONSE FORMATTING"""

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
import re

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

app = FastAPI(title="HealthBot AI", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_response(text: str) -> str:
    """Format AI response for better readability"""
    if not text:
        return text
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'###\s*', '', text)
    
    # Format numbered lists
    lines = text.split('\n')
    formatted_lines = []
    list_counter = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append('')
            continue
        
        # Check for numbered list patterns
        if re.match(r'^\d+[\.\)]\s', line):
            # Already numbered, keep as is
            formatted_lines.append(line)
            list_counter = 1
        elif re.match(r'^[-•*]\s', line):
            # Convert bullet to numbered
            formatted_lines.append(f"{list_counter}. {line[2:]}")
            list_counter += 1
        elif re.match(r'^[A-Za-z]\)\s', line):
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
            list_counter = 1
    
    # Join with proper spacing
    result = '\n'.join(formatted_lines)
    
    # Add emojis for better visual appeal
    if 'blood pressure' in result.lower():
        result = '💓 ' + result
    elif 'headache' in result.lower():
        result = '🤕 ' + result
    elif 'diabetes' in result.lower():
        result = '🩸 ' + result
    elif 'fever' in result.lower():
        result = '🌡️ ' + result
    elif 'heart' in result.lower():
        result = '❤️ ' + result
    
    return result

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

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
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register")
async def register(user: UserRegister):
    try:
        existing = users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
        if existing:
            raise HTTPException(400, "Username or email already exists")
        
        hashed_password = hash_password(user.password)
        user_doc = {
            "username": user.username,
            "email": user.email,
            "password": hashed_password,
            "full_name": user.full_name,
            "created_at": datetime.now(),
            "role": "user"
        }
        result = users.insert_one(user_doc)
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
        raise HTTPException(500, f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login(user: UserLogin):
    try:
        db_user = users.find_one({"username": {"$regex": f"^{user.username}$", "$options": "i"}})
        if not db_user or not verify_password(user.password, db_user["password"]):
            raise HTTPException(401, "Invalid username or password")
        
        token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(db_user["_id"]),
            "username": db_user["username"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login failed: {str(e)}")

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    try:
        print(f"\n💬 CHAT: {token_data.get('sub')} -> {request.message[:50]}...")
        
        response_text = None
        
        if co:
            try:
                # Enhanced prompt for better formatting
                enhanced_prompt = f"""You are HealthBot AI, a helpful medical assistant. Provide a clear, well-formatted response to the following health question.

User Question: {request.message}

Please respond in a clean, readable format with:
- Brief introduction
- Bullet points for key information (use numbers like 1., 2., 3.)
- Clear sections with line breaks
- Friendly, helpful tone

Response:"""

                chat_response = co.chat(
                    message=enhanced_prompt,
                    model="command-a-03-2025",
                    temperature=0.7,
                    max_tokens=500
                )
                
                if chat_response and chat_response.text:
                    response_text = chat_response.text.strip()
                    response_text = format_response(response_text)
                    print(f"  ✅ AI response generated")
            except Exception as e:
                print(f"  ⚠️ AI error: {e}")
        
        if not response_text:
            response_text = get_formatted_response(request.message)
        
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

def get_formatted_response(message: str) -> str:
    """Get formatted fallback response"""
    msg_lower = message.lower()
    
    responses = {
        "blood pressure": """💓 **About Blood Pressure**

1. Normal blood pressure is around 120/80 mmHg
2. Regular monitoring is important for heart health
3. Healthy lifestyle helps maintain good BP
4. Consult your doctor for personalized advice

*Note: This is general information. Please consult a healthcare professional for medical advice.*""",

        "headache": """🤕 **About Headaches**

1. Common causes include:
   • Dehydration - drink more water
   • Eye strain - take regular breaks
   • Stress - try relaxation techniques
   • Lack of sleep - maintain regular schedule

2. Relief tips:
   • Rest in a quiet, dark room
   • Apply cold or warm compress
   • Stay hydrated
   • Use OTC pain relievers if needed

*See a doctor if headaches are severe or persistent*""",

        "diabetes": """🩸 **About Diabetes Management**

1. **Monitor blood sugar** regularly as prescribed
2. **Take medications** exactly as directed
3. **Maintain healthy diet** with balanced nutrition
4. **Exercise regularly** (150 minutes per week)
5. **Regular check-ups** with your healthcare provider

*Always follow your doctor's advice for your specific situation*""",

        "fever": """🌡️ **Fever Management**

1. **Rest** and get plenty of sleep
2. **Stay hydrated** with water and clear fluids
3. **Monitor temperature** every 4-6 hours
4. **Use fever reducers** as needed (acetaminophen/ibuprofen)

**Seek medical attention if:**
• Fever exceeds 103°F (39.4°C)
• Fever lasts more than 3 days
• Accompanied by severe symptoms

*This is general guidance. Consult a doctor for persistent fever*"""
    }
    
    for key, response in responses.items():
        if key in msg_lower:
            return response
    
    return f"""📋 **Health Information**

Thank you for your question about: "{message[:100]}"

I'm a health assistant that can help with:
• Blood pressure and heart health
• Headaches and pain management
• Diabetes care and prevention
• Fever and general symptoms

Please provide more specific details about your health concern so I can give you better information.

*For serious medical concerns, please consult a healthcare professional immediately*"""

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - IMPROVED RESPONSE FORMATTING")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Database: MongoDB Atlas")
    print(f"AI: {'ACTIVE' if co else 'INACTIVE'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
