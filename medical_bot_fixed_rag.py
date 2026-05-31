# medical_bot_fixed_rag.py
"""MEDICAL CHATBOT WITH WORKING RAG"""

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

# Try RAG with correct imports
rag_enabled = False
try:
    # Correct import path for newer LangChain
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    
    # Medical knowledge base
    medical_docs = [
        Document(page_content="Blood Pressure: Normal is 120/80 mmHg. Prevention: Reduce sodium, exercise 150 min/week, maintain healthy weight.",
                 metadata={"topic": "blood_pressure"}),
        Document(page_content="Heart Attack Signs: Chest pain, pain in left arm/jaw, shortness of breath, cold sweat. Call 911 immediately.",
                 metadata={"topic": "heart_attack"}),
        Document(page_content="Diabetes Management: Monitor blood sugar, take medications, healthy diet, exercise 150 min/week.",
                 metadata={"topic": "diabetes"}),
        Document(page_content="Headache Relief: Rest in dark room, hydrate, cold compress. See doctor if severe.",
                 metadata={"topic": "headache"}),
        Document(page_content="Leg Pain Causes: Muscle strain, sciatica, poor circulation. Rest, ice, elevation. See doctor if persistent.",
                 metadata={"topic": "leg_pain"}),
        Document(page_content="Fever: Temperature above 100.4°F. Rest, hydrate, fever reducers. Seek care if >103°F or >3 days.",
                 metadata={"topic": "fever"}),
    ]
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(medical_docs)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory="./medical_db")
    rag_enabled = True
    print(f"✅ RAG Enabled: {len(chunks)} chunks")
    
except ImportError as e:
    print(f"⚠️ RAG packages not installed: {e}")
except Exception as e:
    print(f"⚠️ RAG error: {e}")

app = FastAPI(title="MediBot AI", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv('SECRET_KEY', 'medical-secret-key-2026-32-chars-long-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
security = HTTPBearer()

class UserLogin(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

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
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active" if co else "inactive", "rag": "active" if rag_enabled else "inactive"}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user:
        # Create demo user if not exists
        if user.username == "ab" and user.password == "ab123":
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw("ab123".encode(), salt).decode()
            users.insert_one({"username": "ab", "password": hashed, "created_at": datetime.now()})
            db_user = users.find_one({"username": "ab"})
        else:
            raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": user.username, "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "username": user.username}

# Medical keywords
MEDICAL_KEYWORDS = ['blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'migraine', 'pain', 'fever', 'cold', 'flu', 'cough', 'symptom', 'medication', 'doctor', 'hospital', 'health', 'leg pain', 'back pain']

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

def get_human_response(query: str) -> str:
    """Generate human-like conversational response"""
    q = query.lower()
    
    if "leg pain" in q:
        return """I understand you're experiencing leg pain. Let me help you understand what might be going on.

**To help you better, could you share a few details?**

• Where exactly is the pain? (calf, thigh, behind the knee?)
• What does it feel like? (sharp, dull, burning, cramping?)
• When did it start? (sudden or gradual?)
• Any swelling, redness, or warmth?

**Common causes of leg pain:**

1. **Muscle strain** - Most common, from overuse or dehydration
2. **Sciatica** - Pain radiating from lower back down the leg
3. **Poor circulation** - Cramping pain during activity

**Quick relief tips:**
• Rest and elevate the leg
• Apply ice for 15-20 minutes
• Stay hydrated
• Gentle stretching if it's a cramp

**When to see a doctor:**
• Severe or worsening pain
• Swelling, redness, or warmth
• Difficulty walking
• Pain after injury

*Would you like me to help with anything specific about your leg pain?*"""
    
    elif "blood pressure" in q:
        return """Great question about blood pressure!

**Normal blood pressure is around 120/80 mmHg**

Here's what the numbers mean:
• **Normal:** Less than 120/80
• **Elevated:** 120-129/<80
• **High BP Stage 1:** 130-139/80-89
• **High BP Stage 2:** 140+/90+

**Lifestyle changes that help:**
1. Reduce salt intake (under 2300mg/day)
2. Exercise 30 minutes daily
3. Maintain healthy weight
4. Limit alcohol
5. Manage stress

*Would you like specific tips for any of these areas?*"""
    
    elif "headache" in q:
        return """Headaches can really ruin your day. Let me help!

**Quick relief tips:**
• Rest in a dark, quiet room
• Apply a cold or warm compress
• Stay hydrated (dehydration is a common trigger)
• Try OTC pain relievers like ibuprofen or acetaminophen

**Common triggers to watch for:**
• Stress and tension
• Eye strain from screens
• Lack of sleep
• Caffeine withdrawal
• Certain foods

**When to see a doctor:**
• Severe or "worst headache of your life"
• Headache after head injury
• With fever or stiff neck
• Worsening pattern

*What seems to trigger your headaches?*"""
    
    elif "diabetes" in q:
        return """Managing diabetes is a journey. Here's what helps:

**Blood sugar targets:**
• Before meals: 80-130 mg/dL
• After meals: Less than 180 mg/dL
• A1C: Less than 7%

**Daily management tips:**
1. Monitor blood sugar regularly
2. Take medications as prescribed
3. Eat balanced meals (protein + fiber + healthy carbs)
4. Stay active (walk 30 min daily)
5. Stay hydrated with water

**Watch for low blood sugar (below 70):**
• Shakiness, sweating, confusion
• Fast heartbeat, hunger
→ Eat 15g fast-acting carbs, wait 15 min, recheck

*Would you like meal planning tips or exercise suggestions?*"""
    
    else:
        return f"""Thanks for asking about "{query[:80]}"

I'm a medical assistant specialized in:
• 💓 Blood pressure and heart health
• 🤕 Headaches and pain relief
• 🦵 Leg pain and mobility
• 🩸 Diabetes management
• 🌡️ Fever and general symptoms

**Could you tell me more about what you're experiencing?**

The more details you share, the better I can help!

*For medical emergencies, please call 911 immediately.*"""

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Leg pain\n• Diabetes\n• Fever\n\nWhat health concern can I help with today?"
    else:
        # Use RAG if available, else use human response
        if rag_enabled and 'vectorstore' in dir():
            try:
                docs = vectorstore.similarity_search(query, k=3)
                if docs:
                    context = "\n".join([doc.page_content for doc in docs])
                    if co:
                        prompt = f"""You are a helpful medical assistant. Answer this question conversationally:

User: {query}

Medical context: {context}

Provide a warm, helpful response. Ask follow-up questions. Be specific and practical."""
                        co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=500)
                        response = co_response.text if co_response and co_response.text else get_human_response(query)
                    else:
                        response = get_human_response(query)
                else:
                    response = get_human_response(query)
            except:
                response = get_human_response(query)
        else:
            response = get_human_response(query)
    
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
    print("🏥 MEDIBOT AI - HUMAN-LIKE RESPONSES")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Health: http://localhost:8000/health")
    print(f"RAG: {'ENABLED' if rag_enabled else 'DISABLED (using human responses)'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
