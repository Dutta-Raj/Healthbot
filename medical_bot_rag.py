# medical_bot_rag.py
"""MEDICAL CHATBOT WITH RAG (Retrieval-Augmented Generation)"""

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

# RAG Setup - Medical Knowledge Base
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    
    # Medical knowledge base
    medical_docs = [
        Document(page_content="""Blood Pressure: Normal is 120/80 mmHg. Prevention: Reduce sodium (<2300mg/day), exercise 150 min/week, maintain healthy weight, limit alcohol, manage stress.""", 
                 metadata={"topic": "blood_pressure", "source": "medical_guide"}),
        Document(page_content="""Heart Attack Warning Signs: Chest pain/pressure, pain radiating to left arm/jaw/back, shortness of breath, cold sweat, nausea. CALL 911 IMMEDIATELY.""",
                 metadata={"topic": "heart_attack", "source": "emergency_guide"}),
        Document(page_content="""Diabetes Management: Monitor blood sugar, take medications as prescribed, healthy diet (low sugar, high fiber), exercise 150 min/week, regular check-ups.""",
                 metadata={"topic": "diabetes", "source": "medical_guide"}),
        Document(page_content="""Headache Relief: Rest in dark quiet room, stay hydrated, use cold/warm compress, OTC pain relievers. See doctor if severe or persistent.""",
                 metadata={"topic": "headache", "source": "medical_guide"}),
        Document(page_content="""Fever Management: Rest, hydration, fever reducers (acetaminophen/ibuprofen). Seek care if >103°F, >3 days, or with severe symptoms.""",
                 metadata={"topic": "fever", "source": "medical_guide"}),
        Document(page_content="""COVID-19: Symptoms: fever, cough, shortness of breath, fatigue, loss of taste/smell. Prevention: vaccination, masking, hand hygiene.""",
                 metadata={"topic": "covid", "source": "cdc_guidelines"}),
    ]
    
    # Split and embed
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(medical_docs)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory="./medical_rag_db")
    print(f"✅ RAG Initialized: {len(chunks)} chunks in vector DB")
    rag_enabled = True
except Exception as e:
    print(f"⚠️ RAG not available: {e}")
    rag_enabled = False

app = FastAPI(title="Medical Chatbot with RAG", version="6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = os.getenv('SECRET_KEY', 'medical-secret-key-2026-32-chars-long-here')
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
        "rag": "active" if rag_enabled else "inactive",
        "kafka": os.getenv('KAFKA_ENABLED', 'false')
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
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(401, "Invalid username or password")
    
    token = create_token({"sub": db_user["username"], "user_id": str(db_user["_id"])})
    return {"access_token": token, "token_type": "bearer", "user_id": str(db_user["_id"]), "username": db_user["username"]}

# Medical keywords
MEDICAL_KEYWORDS = [
    'blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'migraine', 
    'pain', 'fever', 'cold', 'flu', 'cough', 'symptom', 'medication',
    'doctor', 'hospital', 'health', 'leg pain', 'back pain', 'covid'
]

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        response = "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Diabetes\n• Fever\n• Heart health"
        return {"response": response, "timestamp": datetime.now().isoformat()}
    
    # Retrieve context from RAG if available
    context = ""
    if rag_enabled and vectorstore:
        try:
            docs = vectorstore.similarity_search(query, k=3)
            if docs:
                context = "\n\n".join([f"• {doc.page_content}" for doc in docs])
                print(f"  📚 Retrieved {len(docs)} relevant documents")
        except Exception as e:
            print(f"RAG error: {e}")
    
    # Generate response with Cohere
    if co:
        try:
            if context:
                prompt = f"""You are a medical assistant. Use this medical context to answer the question.

MEDICAL CONTEXT:
{context}

USER QUESTION: {query}

Provide a clear, helpful response based on the medical information above."""
            else:
                prompt = f"Answer this medical question helpfully: {query}"
            
            co_response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=400)
            response = co_response.text if co_response and co_response.text else get_basic_response(query)
        except:
            response = get_basic_response(query)
    else:
        response = get_basic_response(query)
    
    # Add RAG note if context was used
    if context:
        response += "\n\n---\n📚 *Based on medical knowledge base*"
    
    # Save conversation
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response,
        "rag_used": bool(context),
        "timestamp": datetime.now()
    })
    
    return {"response": response, "timestamp": datetime.now().isoformat()}

def get_basic_response(query: str) -> str:
    q = query.lower()
    if "blood pressure" in q:
        return "**Blood Pressure Guide**\n\nNormal: <120/80 mmHg\nElevated: 120-129/<80\nStage 1: 130-139/80-89\nStage 2: 140+/90+\n\n**Lifestyle:** Reduce sodium, exercise 150 min/week, maintain healthy weight."
    elif "headache" in q:
        return "**Headache Relief**\n\n• Rest in dark, quiet room\n• Stay hydrated\n• Use cold/warm compress\n• OTC pain relievers if needed\n\nSee doctor if severe or persistent."
    elif "diabetes" in q:
        return "**Diabetes Management**\n\n• Monitor blood sugar\n• Take medications as prescribed\n• Healthy diet (low sugar, high fiber)\n• Exercise 150 min/week\n• Regular check-ups"
    else:
        return "I'm a medical assistant. I can help with blood pressure, headaches, diabetes, fever, and heart health. Please ask a specific medical question."

@app.get("/rag/status")
async def rag_status():
    return {"enabled": rag_enabled, "documents": len(chunks) if rag_enabled else 0}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "rag_used": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDICAL CHATBOT - WITH RAG")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"RAG: {'ENABLED' if rag_enabled else 'DISABLED'}")
    print(f"Kafka: {os.getenv('KAFKA_ENABLED', 'false')}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
