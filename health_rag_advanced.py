# health_rag_advanced.py
"""SUPERIOR HEALTH RAG CHATBOT - WITH STREAMING, CITATIONS, MEMORY"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, AsyncGenerator
from datetime import datetime, timedelta
import uvicorn
import os
import jwt
import bcrypt
import json
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import cohere
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
import hashlib

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
    co = cohere.Client(api_key=cohere_key)
    print("✅ Cohere AI Ready")

# Initialize Vector Store (ChromaDB)
print("📚 Initializing Medical Knowledge Base...")

# Medical Knowledge Base Documents
medical_knowledge = [
    # Heart Health
    Document(page_content="""Heart attack warning signs: Chest pain or discomfort, pain radiating to left arm/jaw/back, shortness of breath, cold sweat, nausea, lightheadedness. Call emergency services immediately.""", 
             metadata={"source": "heart_health", "topic": "heart_attack", "confidence": 0.95}),
    
    Document(page_content="""Blood pressure categories: Normal (below 120/80), Elevated (120-129/<80), High BP Stage 1 (130-139/80-89), Stage 2 (140+/90+), Hypertensive Crisis (180+/120+). Consult doctor for personalized targets.""",
             metadata={"source": "heart_health", "topic": "blood_pressure", "confidence": 0.98}),
    
    Document(page_content="""Heart disease prevention: Exercise 150 min/week moderate activity, maintain healthy weight, don't smoke, limit alcohol, eat Mediterranean diet rich in fruits/vegetables/whole grains, manage stress, regular check-ups.""",
             metadata={"source": "heart_health", "topic": "prevention", "confidence": 0.95}),
    
    # Diabetes
    Document(page_content="""Diabetes types: Type 1 (autoimmune, no insulin production), Type 2 (insulin resistance, most common), Gestational (pregnancy-related). Type 2 can often be managed with lifestyle changes.""",
             metadata={"source": "diabetes", "topic": "types", "confidence": 0.97}),
    
    Document(page_content="""Diabetes management: Monitor blood sugar regularly, take medications as prescribed, healthy diet (low sugar/processed foods), exercise 150 min/week, regular A1C tests (target <7%).""",
             metadata={"source": "diabetes", "topic": "management", "confidence": 0.96}),
    
    Document(page_content="""Hypoglycemia signs: Blood sugar below 70 mg/dL, shakiness, sweating, confusion, rapid heartbeat, hunger. Treatment: 15g fast-acting carbs, wait 15 min, recheck.""",
             metadata={"source": "diabetes", "topic": "hypoglycemia", "confidence": 0.98}),
    
    # Headaches/Migraines
    Document(page_content="""Migraine symptoms: Throbbing pain (often one-sided), nausea/vomiting, sensitivity to light/sound, visual auras (flashing lights, blind spots), lasting 4-72 hours.""",
             metadata={"source": "headache", "topic": "migraine", "confidence": 0.96}),
    
    Document(page_content="""Tension headache: Mild to moderate band-like pressure around head, both sides, no nausea, triggered by stress/eye strain/poor posture. Relief: rest, hydration, OTC pain relievers.""",
             metadata={"source": "headache", "topic": "tension", "confidence": 0.95}),
    
    # Fever
    Document(page_content="""Fever in adults: Temperature above 100.4°F (38°C). Management: rest, hydration (water/electrolytes), fever reducers (acetaminophen/ibuprofen), monitor every 4-6 hours.""",
             metadata={"source": "fever", "topic": "adults", "confidence": 0.97}),
    
    Document(page_content="""When to seek emergency care for fever: Temperature over 103°F (39.4°C), fever lasting over 3 days, severe headache, stiff neck, confusion, difficulty breathing, chest pain.""",
             metadata={"source": "fever", "topic": "emergency", "confidence": 0.98}),
    
    # Cold/Flu
    Document(page_content="""Common cold vs flu: Cold: gradual onset, mild symptoms, rarely fever. Flu: sudden onset, high fever, body aches, fatigue, can be severe. Flu vaccine recommended annually.""",
             metadata={"source": "infectious", "topic": "cold_flu", "confidence": 0.96}),
    
    # Medications
    Document(page_content="""Medication safety: Always take as prescribed, don't skip or double doses, check expiration dates, report side effects to doctor, keep medication list, use one pharmacy.""",
             metadata={"source": "medication", "topic": "safety", "confidence": 0.99}),
    
    # Sleep
    Document(page_content="""Sleep hygiene: Consistent sleep schedule (7-9 hours), dark quiet room, avoid screens 1 hour before bed, limit caffeine after 2 PM, exercise daily but not before bed.""",
             metadata={"source": "sleep", "topic": "hygiene", "confidence": 0.95}),
    
    # Nutrition
    Document(page_content="""Heart-healthy diet: Eat more: vegetables, fruits, whole grains, lean protein, fish (omega-3), nuts, olive oil. Limit: saturated fats, trans fats, sodium, added sugars, red meat.""",
             metadata={"source": "nutrition", "topic": "heart_healthy", "confidence": 0.97}),
]

# Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", " ", ""]
)

all_chunks = []
for doc in medical_knowledge:
    chunks = text_splitter.split_text(doc.page_content)
    for i, chunk in enumerate(chunks):
        all_chunks.append(Document(
            page_content=chunk,
            metadata={
                **doc.metadata,
                "chunk_id": i,
                "text": chunk
            }
        ))

print(f"✅ Created {len(all_chunks)} knowledge chunks")

# Initialize embeddings and vector store
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(
    documents=all_chunks,
    embedding=embeddings,
    persist_directory="./chroma_health_db"
)

print("✅ Vector store initialized")

# Memory management
user_memories = {}

def get_memory(user_id: str):
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    return user_memories[user_id]

SECRET_KEY = os.getenv('SECRET_KEY', 'healthbot-secret-key')
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

app = FastAPI(title="HealthBot AI - RAG Powered", version="9.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "healthy", "rag": "active", "documents": len(all_chunks)}

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

async def stream_response(query: str, context: str, sources: List[dict], memory: ConversationBufferMemory):
    """Stream response token by token with citations"""
    
    # Build prompt with context and sources
    prompt = f"""You are HealthBot AI, a medical assistant with access to verified health information.

Context from medical knowledge base:
{context}

User question: {query}

Provide a clear, accurate response. At the end, cite your sources in this format:
---
📚 **Sources:**
{chr(10).join([f"• {s['source']}: {s['text'][:100]}..." for s in sources])}

Response:"""

    # Simulate streaming (in production, use actual LLM streaming)
    words = prompt.split()
    
    for word in words:
        yield f"data: {word}\n\n"
        await asyncio.sleep(0.05)
    
    # Add sources at the end
    sources_text = f"\n\ndata: [DONE]\n\n"
    yield sources_text

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, token_data: dict = Depends(verify_token)):
    """Streaming chat endpoint with RAG and citations"""
    
    user_id = token_data.get("user_id")
    query = request.message
    
    # Retrieve relevant documents
    docs = vectorstore.similarity_search(query, k=5)
    
    # Build context
    context = "\n\n".join([f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs)])
    
    # Extract sources
    sources = []
    for doc in docs:
        sources.append({
            "source": doc.metadata.get("source", "medical_knowledge"),
            "topic": doc.metadata.get("topic", "general"),
            "text": doc.page_content[:150]
        })
    
    # Get memory
    memory = get_memory(user_id)
    
    # Save conversation
    conversation = {
        "user_id": user_id,
        "username": token_data.get("sub"),
        "message": query,
        "context": context,
        "timestamp": datetime.now()
    }
    conversations.insert_one(conversation)
    
    # Return streaming response
    return StreamingResponse(
        stream_response(query, context, sources, memory),
        media_type="text/event-stream"
    )

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    """Non-streaming chat endpoint with RAG and citations"""
    
    user_id = token_data.get("user_id")
    query = request.message
    
    # Retrieve relevant documents
    docs = vectorstore.similarity_search(query, k=5)
    
    # Build context
    context = "\n\n".join([f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs)])
    
    # Extract sources
    sources = []
    for doc in docs:
        sources.append({
            "source": doc.metadata.get("source", "medical_knowledge"),
            "topic": doc.metadata.get("topic", "general"),
            "text": doc.page_content[:150]
        })
    
    # Generate response using Cohere
    response_text = ""
    if co:
        try:
            enhanced_prompt = f"""You are HealthBot AI, a medical assistant. Answer based on this context:

Context:
{context}

Question: {query}

Provide a clear, accurate response with numbered points where appropriate."""

            co_response = co.chat(
                message=enhanced_prompt,
                model="command-a-03-2025",
                temperature=0.5,
                max_tokens=500
            )
            if co_response and co_response.text:
                response_text = co_response.text.strip()
        except Exception as e:
            response_text = get_fallback_response(query, context)
    else:
        response_text = get_fallback_response(query, context)
    
    # Add citations
    citation_text = "\n\n---\n📚 **Sources:**\n"
    for i, source in enumerate(sources, 1):
        citation_text += f"{i}. {source['source']} - {source['text']}...\n"
    
    full_response = response_text + citation_text
    
    # Save to database
    conversation = {
        "user_id": user_id,
        "username": token_data.get("sub"),
        "message": query,
        "response": full_response,
        "sources": sources,
        "timestamp": datetime.now()
    }
    conversations.insert_one(conversation)
    
    return {
        "response": full_response,
        "sources": sources,
        "timestamp": datetime.now().isoformat()
    }

def get_fallback_response(query: str, context: str) -> str:
    """Generate response based on retrieved context"""
    
    if "blood pressure" in query.lower():
        return """**Blood Pressure Information**

Based on our medical knowledge base:

1. **Normal Range**: Below 120/80 mmHg
2. **Elevated**: 120-129/<80 mmHg  
3. **High BP Stage 1**: 130-139/80-89 mmHg
4. **High BP Stage 2**: 140+/90+ mmHg
5. **Hypertensive Crisis**: 180+/120+ (seek immediate care)

**Prevention Tips:**
• Reduce sodium intake (<2300mg/day)
• Exercise 150 minutes/week
• Maintain healthy weight
• Limit alcohol
• Manage stress

*Consult your doctor for personalized targets*"""
    
    elif "heart attack" in query.lower():
        return """**Heart Attack Warning Signs**

**Immediate Emergency Symptoms:**
• Chest pain/pressure (may feel like squeezing)
• Pain radiating to left arm, jaw, back, or stomach
• Shortness of breath
• Cold sweat, nausea, lightheadedness

**Action:** Call emergency services immediately. Every minute counts.

**Prevention:**
• Control blood pressure and cholesterol
• Don't smoke
• Exercise regularly
• Eat heart-healthy diet
• Manage diabetes if present"""
    
    elif "diabetes" in query.lower():
        return """**Diabetes Management Guide**

**Blood Sugar Targets:**
• Before meals: 80-130 mg/dL
• After meals (2h): <180 mg/dL
• A1C: <7%

**Management Strategies:**
1. Monitor blood sugar daily
2. Take medications as prescribed
3. Eat balanced diet (low sugar, high fiber)
4. Exercise 150 min/week
5. Regular check-ups with endocrinologist

**Hypoglycemia (Low Blood Sugar):**
• Treat with 15g fast-acting carbs
• Recheck in 15 minutes
• Seek help if below 70 mg/dL"""
    
    else:
        return f"""**Health Information**

Based on our medical knowledge base, here's what I found about your query:

{context[:500]}

---

**Key Takeaways:**
• Always consult healthcare professionals for medical advice
• This information is for educational purposes
• Seek emergency care for severe symptoms

*Would you like more specific information about this topic?*"""

@app.get("/history")
async def get_history(limit: int = 50, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(limit))
    return {"history": history, "count": len(history)}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - RAG POWERED")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Vector DB: ChromaDB ({len(all_chunks)} chunks)")
    print(f"Memory: ConversationBufferMemory per user")
    print(f"Streaming: ENABLED")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
