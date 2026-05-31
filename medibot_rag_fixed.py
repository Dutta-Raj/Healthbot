# medibot_rag_fixed.py
"""MEDIBOT AI - WITH WORKING RAG (no deprecation warnings)"""

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

# RAG Setup - Using correct imports
rag_enabled = False
vectorstore = None

try:
    # Correct imports for 2026
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    import chromadb
    
    # Create medical knowledge base
    medical_docs = [
        Document(page_content="Blood Pressure: Normal is 120/80 mmHg. High blood pressure has no symptoms but damages arteries. Prevention: Reduce sodium (<2300mg/day), exercise 150 min/week, maintain healthy weight, limit alcohol, manage stress.",
                 metadata={"source": "medical_guide", "topic": "blood_pressure"}),
        
        Document(page_content="Heart Attack Warning Signs: Chest pain or pressure, pain radiating to left arm/jaw/back, shortness of breath, cold sweat, nausea, lightheadedness. CALL 911 IMMEDIATELY if you experience these symptoms.",
                 metadata={"source": "emergency_guide", "topic": "heart_attack"}),
        
        Document(page_content="Diabetes Management: Type 2 diabetes can be managed with lifestyle changes. Monitor blood sugar regularly, take medications as prescribed, eat balanced meals (protein+fiber+healthy carbs), exercise 150 min/week, maintain healthy weight.",
                 metadata={"source": "medical_guide", "topic": "diabetes"}),
        
        Document(page_content="Headache Relief: Tension headaches respond to rest, hydration, OTC pain relievers. Migraines may need prescription medication. Common triggers: stress, lack of sleep, dehydration, certain foods, eye strain.",
                 metadata={"source": "medical_guide", "topic": "headache"}),
        
        Document(page_content="Leg Pain Causes: Muscle strain (most common - from overuse/dehydration), sciatica (nerve pain from lower back), poor circulation (PAD), DVT (blood clot - medical emergency). Try RICE: Rest, Ice, Compression, Elevation.",
                 metadata={"source": "medical_guide", "topic": "leg_pain"}),
        
        Document(page_content="Fever Management: Temperature above 100.4°F (38°C). Rest, stay hydrated, use fever reducers (acetaminophen/ibuprofen). Seek care if: >103°F, >3 days, severe headache, stiff neck, confusion, difficulty breathing.",
                 metadata={"source": "medical_guide", "topic": "fever"}),
        
        Document(page_content="COVID-19 Symptoms: Fever, cough, shortness of breath, fatigue, loss of taste/smell, body aches. Prevention: Vaccination, masking in crowds, hand hygiene, social distancing when cases are high.",
                 metadata={"source": "cdc", "topic": "covid"}),
        
        Document(page_content="Anxiety and Stress: Common symptoms: racing thoughts, rapid heartbeat, difficulty sleeping, restlessness. Management: Deep breathing exercises, regular exercise, adequate sleep, limit caffeine, talk to someone, consider therapy.",
                 metadata={"source": "mental_health", "topic": "anxiety"}),
    ]
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(medical_docs)
    print(f"  ✅ Created {len(chunks)} document chunks")
    
    # Create embeddings and vector store
    print("  🔄 Loading embeddings model (first time may take a moment)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Use ChromaDB directly
    vectorstore = chromadb.PersistentClient(path="./chroma_medical_db")
    collection = vectorstore.get_or_create_collection(name="medical_knowledge")
    
    # Add documents to ChromaDB
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk.page_content],
            metadatas=[chunk.metadata],
            ids=[f"doc_{i}"]
        )
    
    rag_enabled = True
    print(f"✅ RAG ENABLED: {len(chunks)} medical documents loaded")
    
except ImportError as e:
    print(f"⚠️ RAG package missing: {e}")
    print("   Run: pip install langchain-huggingface chromadb sentence-transformers")
except Exception as e:
    print(f"⚠️ RAG setup error: {e}")

app = FastAPI(title="MediBot AI with RAG", version="4.0")
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
    'leg pain', 'back pain', 'covid', 'anxiety', 'stress', 'symptom'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

def search_rag(query: str) -> str:
    """Search RAG database for relevant medical info"""
    if not rag_enabled or not vectorstore:
        return ""
    
    try:
        results = collection.query(query_texts=[query], n_results=3)
        if results['documents'] and results['documents'][0]:
            return "\n\n".join(results['documents'][0])
    except Exception as e:
        print(f"RAG search error: {e}")
    
    return ""

def get_human_response(query: str, context: str = "") -> str:
    """Generate human-like response with RAG context"""
    q = query.lower()
    
    # If we have RAG context, use it to enhance response
    if context:
        return f"""Based on medical knowledge, here's what I found about your question:

{context}

---

**In simple terms:**

{get_simple_response(q)}

*Would you like me to explain any of this in more detail?* 💙"""
    
    return get_simple_response(q)

def get_simple_response(q: str) -> str:
    """Simple response without RAG"""
    if "leg pain" in q:
        return """I hear you're dealing with leg pain. 

**Quick relief:**
1. Rest the leg
2. Ice for 15-20 minutes
3. Elevate above heart level

**See a doctor if:** Severe pain, swelling, redness, or difficulty walking.

*Where exactly does it hurt? I can give more specific advice.* 💙"""
    
    elif "blood pressure" in q:
        return """**Normal blood pressure: less than 120/80 mmHg**

**Lifestyle changes that help:**
• Reduce salt intake
• Exercise 30 min daily
• Maintain healthy weight
• Limit alcohol
• Manage stress

*Would you like specific tips for any of these?* ❤️"""
    
    elif "headache" in q:
        return """**Quick relief:**
• Rest in dark, quiet room
• Stay hydrated
• Cold compress on forehead
• OTC pain reliever if needed

**Common triggers:** Stress, lack of sleep, dehydration, eye strain.

*What usually triggers your headaches?* 🤕"""
    
    elif "diabetes" in q:
        return """**Diabetes management basics:**
1. Monitor blood sugar
2. Take medications as prescribed
3. Eat balanced meals
4. Exercise 30 min daily
5. Stay hydrated

*Would you like meal planning tips?* 🩸"""
    
    else:
        return "I'm here to help with medical questions about blood pressure, headaches, leg pain, diabetes, and fever. What would you like to know?"

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Leg pain\n• Diabetes\n• Fever\n• Heart health"
        return {"response": response, "timestamp": datetime.now().isoformat()}
    
    # Search RAG for relevant context
    context = search_rag(query) if rag_enabled else ""
    
    # Generate response
    if co and rag_enabled:
        try:
            prompt = f"""You are MediBot AI, a warm medical assistant.

Medical knowledge from our database:
{context if context else "No specific medical context retrieved"}

User question: {query}

Provide a helpful, accurate response based on the medical knowledge above. Be warm and conversational. Include practical tips. Ask a follow-up question at the end."""
            
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
    return {"enabled": rag_enabled, "message": "RAG is active and retrieving medical knowledge" if rag_enabled else "RAG is disabled"}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "rag_used": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDIBOT AI - WITH WORKING RAG")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"RAG: {'ENABLED ✅' if rag_enabled else 'DISABLED'}")
    print(f"Health: http://localhost:8000/health")
    print(f"RAG Status: http://localhost:8000/rag/status")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
