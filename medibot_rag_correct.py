# medibot_rag_correct.py
"""MEDIBOT AI - CORRECT RAG IMPLEMENTATION"""

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

# Cohere AI
co = None
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    try:
        co = cohere.Client(api_key=cohere_key)
        print("✅ Cohere AI Ready")
    except:
        pass

# Try RAG with correct imports
rag_enabled = False
collection = None

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    
    # Initialize embedding model
    print("  Loading embedding model...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path="./chroma_medical")
    collection = chroma_client.get_or_create_collection(name="medical_knowledge")
    
    # Medical knowledge base
    medical_knowledge = [
        {"id": "doc_1", "text": "Blood Pressure: Normal is 120/80 mmHg. Prevention: Reduce sodium (<2300mg/day), exercise 150 min/week, maintain healthy weight.", "topic": "blood_pressure"},
        {"id": "doc_2", "text": "Heart Attack Signs: Chest pain, pain in left arm/jaw, shortness of breath, cold sweat, nausea. CALL 911 immediately.", "topic": "heart_attack"},
        {"id": "doc_3", "text": "Diabetes Management: Monitor blood sugar, take medications, healthy diet, exercise 150 min/week. A1C target below 7%.", "topic": "diabetes"},
        {"id": "doc_4", "text": "Headache Relief: Rest in dark room, hydrate, cold compress. Migraine triggers: stress, lack of sleep, certain foods.", "topic": "headache"},
        {"id": "doc_5", "text": "Leg Pain Causes: Muscle strain (rest, ice), sciatica (nerve pain from back), DVT (blood clot - medical emergency).", "topic": "leg_pain"},
        {"id": "doc_6", "text": "Fever: Temperature above 100.4°F. Rest, hydrate, fever reducers. Seek care if >103°F or >3 days.", "topic": "fever"},
        {"id": "doc_7", "text": "COVID-19: Symptoms: fever, cough, fatigue, loss of taste/smell. Prevention: vaccination, masking, hand hygiene.", "topic": "covid"},
        {"id": "doc_8", "text": "Anxiety: Deep breathing, exercise, sleep, limit caffeine, talk to someone. Seek help if affecting daily life.", "topic": "anxiety"},
    ]
    
    # Check if collection is empty
    if collection.count() == 0:
        print("  Loading medical knowledge into vector database...")
        for doc in medical_knowledge:
            embedding = embedding_model.encode(doc["text"]).tolist()
            collection.add(
                ids=[doc["id"]],
                embeddings=[embedding],
                documents=[doc["text"]],
                metadatas=[{"topic": doc["topic"]}]
            )
        print(f"  ✅ Loaded {len(medical_knowledge)} documents")
    
    rag_enabled = True
    print("✅ RAG ENABLED - Medical knowledge base ready")
    
except ImportError as e:
    print(f"⚠️ RAG package missing: {e}")
    print("   Run: pip install chromadb sentence-transformers")
except Exception as e:
    print(f"⚠️ RAG error: {e}")

app = FastAPI(title="MediBot AI with RAG", version="5.0")
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
        "rag": "active" if rag_enabled else "inactive"
    }

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
    return {"access_token": token, "token_type": "bearer", "user_id": str(result.inserted_id), "username": user.username}

@app.post("/auth/login")
async def login(user: UserLogin):
    db_user = users.find_one({"username": user.username})
    if not db_user:
        raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"]}

# Medical keywords
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'pain', 'fever',
    'leg pain', 'back pain', 'covid', 'anxiety', 'stress', 'symptom', 'cold', 'flu'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

def search_rag(query: str) -> str:
    """Search RAG for relevant medical information"""
    if not rag_enabled or not collection:
        return ""
    
    try:
        # Generate embedding for query
        embedding = embedding_model.encode(query).tolist()
        
        # Search in ChromaDB
        results = collection.query(query_embeddings=[embedding], n_results=3)
        
        if results['documents'] and results['documents'][0]:
            return "\n\n".join(results['documents'][0])
    except Exception as e:
        print(f"RAG search error: {e}")
    
    return ""

def get_human_response(query: str, context: str = "") -> str:
    """Generate warm, human-like response"""
    q = query.lower()
    
    if context:
        return f"""📚 **Based on medical knowledge:**

{context}

---

**What this means for you:**

{get_simple_response(q)}

*Would you like me to explain anything in more detail?* 💙"""
    
    return get_simple_response(q)

def get_simple_response(q: str) -> str:
    """Simple response without RAG"""
    if "leg pain" in q:
        return """I understand you're experiencing leg pain. Here's what helps:

**Quick relief:**
• Rest the leg
• Ice for 15-20 minutes
• Elevate above heart level
• Gentle stretching if it's a cramp

**See a doctor if:**
• Severe or worsening pain
• Swelling, redness, or warmth
• Difficulty walking
• Pain after injury

*Where exactly does it hurt? I can give more specific advice.* 💙"""
    
    elif "blood pressure" in q:
        return """**Blood Pressure Guide**

Normal: Less than 120/80 mmHg

**Lifestyle changes that work:**
1. Reduce salt (under 2300mg/day)
2. Exercise 30 minutes daily
3. Maintain healthy weight
4. Limit alcohol
5. Manage stress

*Would you like specific tips for any of these?* ❤️"""
    
    elif "headache" in q:
        return """**Headache Relief**

• Rest in dark, quiet room
• Stay hydrated (dehydration is a trigger)
• Cold compress on forehead
• OTC pain reliever if needed

**Common triggers:** Stress, lack of sleep, eye strain, certain foods

*What usually triggers your headaches?* 🤕"""
    
    elif "diabetes" in q:
        return """**Diabetes Management**

**Blood sugar targets:**
• Before meals: 80-130 mg/dL
• After meals: <180 mg/dL
• A1C: <7%

**Daily habits:**
1. Monitor blood sugar
2. Take medications as prescribed
3. Eat balanced meals
4. Exercise 30 min daily
5. Stay hydrated

*Would you like meal planning tips?* 🩸"""
    
    elif "fever" in q:
        return """**Fever Management**

**Temperature guide:**
• 100.4-102°F: Mild fever
• 102-104°F: Moderate - monitor closely
• 104°F+: High - call doctor

**What to do:**
• Rest and stay hydrated
• Use fever reducers if uncomfortable
• Light clothing and blankets

**Seek care if:**
• Fever over 103°F
• Lasts more than 3 days
• Difficulty breathing

*How long have you had the fever?* 🌡️"""
    
    else:
        return "I'm here to help with medical questions about blood pressure, headaches, leg pain, diabetes, fever, and heart health. What would you like to know?"

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Leg pain\n• Diabetes\n• Fever\n• Heart health\n\nWhat health concern can I help with today?"
        return {"response": response, "timestamp": datetime.now().isoformat()}
    
    # Search RAG for relevant context
    context = search_rag(query) if rag_enabled else ""
    
    # Generate response
    if co:
        try:
            if context:
                prompt = f"""You are MediBot AI, a warm medical assistant.

Medical knowledge from our database:
{context}

User question: {query}

Provide a helpful, accurate response based on the medical knowledge above. Be warm and conversational. Include practical tips. End with a helpful follow-up question."""
            else:
                prompt = f"""You are MediBot AI, a warm medical assistant. Answer this health question conversationally: {query}

Be helpful, include practical tips, and end with a follow-up question."""
            
            co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=500)
            if co_response and co_response.text:
                response = co_response.text.strip()
            else:
                response = get_human_response(query, context)
        except:
            response = get_human_response(query, context)
    else:
        response = get_human_response(query, context)
    
    # Save conversation
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response,
        "rag_used": bool(context),
        "timestamp": datetime.now()
    })
    
    return {"response": response, "timestamp": datetime.now().isoformat(), "rag_used": bool(context)}

@app.get("/rag/status")
async def rag_status():
    return {
        "enabled": rag_enabled,
        "documents": collection.count() if rag_enabled and collection else 0,
        "message": "RAG is active and retrieving medical knowledge" if rag_enabled else "RAG is disabled"
    }

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "rag_used": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDIBOT AI - RAG WORKING")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"RAG: {'ENABLED ✅' if rag_enabled else 'DISABLED'}")
    print(f"Documents: {collection.count() if rag_enabled and collection else 0}")
    print(f"RAG Status: http://localhost:8000/rag/status")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
