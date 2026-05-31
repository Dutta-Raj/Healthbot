# medical_bot_working.py
"""WORKING MEDICAL CHATBOT WITH RAG"""

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
    except Exception as e:
        print(f"⚠️ Cohere error: {e}")

# Try to initialize RAG
rag_enabled = False
vectorstore = None

try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    
    # Medical knowledge base
    medical_docs = [
        Document(page_content="Blood Pressure: Normal is 120/80 mmHg. High blood pressure has no symptoms but can cause heart disease. Prevention: reduce sodium, exercise, maintain healthy weight.", 
                 metadata={"topic": "blood_pressure"}),
        Document(page_content="Heart Attack Signs: Chest pain, pain in left arm/jaw/back, shortness of breath, cold sweat, nausea. Call 911 immediately.", 
                 metadata={"topic": "heart_attack"}),
        Document(page_content="Diabetes Management: Type 2 diabetes can be managed with diet, exercise, medication. Monitor blood sugar regularly. A1C target is below 7%.", 
                 metadata={"topic": "diabetes"}),
        Document(page_content="Headache Relief: Tension headaches respond to rest, hydration, OTC pain relievers. Migraines may need prescription medication. See doctor if severe.", 
                 metadata={"topic": "headache"}),
        Document(page_content="Fever: Temperature above 100.4°F. Rest, hydration, fever reducers. Seek care if >103°F or >3 days.", 
                 metadata={"topic": "fever"}),
    ]
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(medical_docs)
    
    # Create embeddings and vector store
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory="./medical_vectordb")
    rag_enabled = True
    print(f"✅ RAG Enabled: {len(chunks)} chunks in vector DB")
    
except Exception as e:
    print(f"⚠️ RAG not available: {e}")

app = FastAPI(title="Medical Chatbot", version="7.0")
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
    return {
        "status": "healthy",
        "database": "MongoDB Atlas",
        "ai": "active" if co else "inactive",
        "rag": "active" if rag_enabled else "inactive"
    }

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
MEDICAL_KEYWORDS = ['blood pressure', 'bp', 'heart', 'diabetes', 'headache', 'migraine', 'pain', 'fever', 'cold', 'flu', 'cough', 'symptom', 'medication', 'doctor', 'hospital', 'health']

def is_medical(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in MEDICAL_KEYWORDS)

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    if not is_medical(query):
        return {"response": "💙 I'm a MEDICAL assistant. I can ONLY answer HEALTH questions.\n\nPlease ask me about:\n• Blood pressure\n• Headaches\n• Diabetes\n• Fever\n• Heart health", "timestamp": datetime.now().isoformat()}
    
    # Try RAG retrieval
    context = ""
    if rag_enabled and vectorstore:
        try:
            docs = vectorstore.similarity_search(query, k=3)
            if docs:
                context = "\n".join([f"• {doc.page_content}" for doc in docs])
                print(f"📚 Retrieved {len(docs)} medical documents")
        except Exception as e:
            print(f"RAG error: {e}")
    
    # Generate response
    if co:
        try:
            if context:
                prompt = f"""You are a medical assistant. Use this medical information to answer.

MEDICAL INFO:
{context}

QUESTION: {query}

Answer helpfully and accurately:"""
            else:
                prompt = f"Answer this medical question: {query}"
            
            response = co.chat(message=prompt, model="command-a-03-2025", temperature=0.7, max_tokens=400)
            response_text = response.text if response and response.text else "I'm here to help with medical questions."
        except Exception as e:
            response_text = f"I'm a medical assistant. Regarding '{query[:100]}', please consult a healthcare professional for accurate advice."
    else:
        response_text = "I'm a medical assistant. I can help with blood pressure, headaches, diabetes, and fever. Please ask a specific health question."
    
    if context:
        response_text += "\n\n---\n📚 *Based on medical knowledge base*"
    
    # Save conversation
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response_text,
        "rag_used": bool(context),
        "timestamp": datetime.now()
    })
    
    return {"response": response_text, "timestamp": datetime.now().isoformat()}

@app.get("/rag/status")
async def rag_status():
    return {"enabled": rag_enabled, "message": "RAG is active and retrieving medical knowledge" if rag_enabled else "RAG is disabled"}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 MEDICAL CHATBOT - WORKING RAG VERSION")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Health: http://localhost:8000/health")
    print(f"RAG Status: http://localhost:8000/rag/status")
    print(f"RAG: {'ENABLED' if rag_enabled else 'DISABLED'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
