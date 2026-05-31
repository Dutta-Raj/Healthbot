# medibot_global.py
"""MEDIBOT AI - GLOBAL MEDICAL INTELLIGENCE (Any Disease, Any Medicine)"""

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
import re
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
        print("✅ Cohere AI Ready (Global Medical Knowledge)")
    except:
        pass

app = FastAPI(title="MediBot AI - Global Medical Intelligence", version="7.0")
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
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active", "intelligence": "global"}

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

# Global medical categories detection
MEDICAL_CATEGORIES = {
    "cardiovascular": ["heart", "cardio", "blood pressure", "hypertension", "stroke", "artery", "vein", "circulation", "cholesterol", "triglycerides"],
    "neurological": ["brain", "headache", "migraine", "seizure", "epilepsy", "dementia", "alzheimer", "parkinson", "neuropathy", "nerve"],
    "respiratory": ["lung", "breathing", "asthma", "cOPD", "pneumonia", "bronchitis", "cough", "shortness of breath", "wheezing"],
    "gastrointestinal": ["stomach", "digestion", "ulcer", "gerd", "acid reflux", "ibs", "crohn", "colitis", "liver", "pancreas"],
    "musculoskeletal": ["bone", "joint", "arthritis", "osteoporosis", "muscle", "ligament", "tendon", "back pain", "neck pain"],
    "endocrine": ["diabetes", "thyroid", "hormone", "cortisol", "insulin", "metabolism", "adrenal", "pituitary"],
    "infectious": ["infection", "virus", "bacteria", "flu", "covid", "pneumonia", "tuberculosis", "hepatitis", "hiv"],
    "mental_health": ["anxiety", "depression", "stress", "insomnia", "bipolar", "ptsd", "ocd", "panic", "therapy", "psychiatrist"],
    "oncology": ["cancer", "tumor", "chemotherapy", "radiation", "oncology", "malignant", "benign", "metastasis"],
    "pediatric": ["child", "baby", "infant", "pediatric", "newborn", "vaccine", "development"],
    "geriatric": ["elderly", "aging", "senior", "dementia", "falls", "osteoporosis"],
    "women_health": ["pregnancy", "menstrual", "menopause", "ovary", "uterine", "breast", "gynecology"],
    "men_health": ["prostate", "testosterone", "erectile", "andropause"],
    "dermatology": ["skin", "rash", "acne", "eczema", "psoriasis", "dermatitis", "melanoma", "hives"],
    "ophthalmology": ["eye", "vision", "cataract", "glaucoma", "retina", "cornea"],
    "dentistry": ["tooth", "gum", "dental", "cavity", "root canal", "orthodontic"],
    "urology": ["kidney", "bladder", "urinary", "uti", "nephrology", "dialysis"],
    "hematology": ["blood", "anemia", "leukemia", "clotting", "hemoglobin"],
    "immunology": ["allergy", "immune", "autoimmune", "lupus", "rheumatoid", "hives"],
    "emergency": ["emergency", "urgent", "911", "ambulance", "poison", "overdose", "trauma"]
}

def detect_medical_category(query: str) -> str:
    """Detect which medical category the query belongs to"""
    query_lower = query.lower()
    for category, keywords in MEDICAL_CATEGORIES.items():
        for keyword in keywords:
            if keyword in query_lower:
                return category
    return "general"

def is_medical_query(query: str) -> bool:
    """Check if query is medical-related"""
    query_lower = query.lower()
    
    # Non-medical patterns
    non_medical = ["weather", "stock", "movie", "game", "sports", "cooking", "recipe", "travel", "flight", "hotel"]
    for nm in non_medical:
        if nm in query_lower:
            return False
    
    # Check if any medical term appears
    for category, keywords in MEDICAL_CATEGORIES.items():
        for keyword in keywords:
            if keyword in query_lower:
                return True
    return False

def get_intelligent_response(query: str, category: str) -> str:
    """Generate intelligent response using Cohere AI for ANY medical question"""
    
    if co:
        try:
            prompt = f"""You are MediBot AI, a compassionate medical assistant with knowledge of ALL medical conditions, diseases, medicines, and treatments.

User Question: {query}
Detected Category: {category}

Provide a helpful, accurate, and compassionate response. Include:
1. Brief explanation of the condition/topic
2. Common symptoms (if applicable)
3. General management tips
4. When to see a doctor
5. A helpful follow-up question

Be conversational, use emojis where appropriate, and always remind that this is educational information.
Keep response under 400 words.

Response:"""
            
            response = co.chat(
                message=prompt,
                model="command-a-03-2025",
                temperature=0.7,
                max_tokens=500
            )
            
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Cohere error: {e}")
    
    # Fallback for any medical query - Dynamic response
    return f"""**📋 Information about your medical query**

I understand you're asking about: "{query[:100]}"

**General Information:**
This appears to be related to {category.replace('_', ' ').title()} health.

**What you should know:**
• Every medical condition is unique to each person
• Symptoms can vary based on individual factors
• Professional medical advice is essential for proper diagnosis

**Recommended next steps:**
1. **Monitor your symptoms** - track when they started, what triggers them
2. **Consult a healthcare provider** - they can provide proper diagnosis
3. **Don't self-medicate** - always follow professional advice

**When to seek immediate care:**
• Severe or sudden symptoms
• Difficulty breathing
• Chest pain
• Loss of consciousness
• Severe allergic reactions

*Would you like me to provide more specific information about this condition?* 💙"""

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    query = request.message
    
    # Check if medical
    if not is_medical_query(query):
        response = f"""💙 **I'm a MEDICAL assistant.**

I can only answer HEALTH-related questions. Please ask me about:
• Any disease or condition (diabetes, asthma, arthritis, etc.)
• Any medicine or treatment
• Symptoms you're experiencing
• General health concerns

**Your question:** "{query[:100]}"

Please rephrase as a medical question. For example:
• "What are the symptoms of pneumonia?"
• "How is high blood pressure treated?"
• "What causes migraine headaches?"

*I'm here to help with any medical topic!* 🏥"""
        
        return {"response": response, "timestamp": datetime.now().isoformat()}
    
    # Detect category for better context
    category = detect_medical_category(query)
    print(f"📚 Detected category: {category} for query: {query[:50]}")
    
    # Get intelligent response
    if co:
        try:
            # Enhanced prompt for ANY medical condition
            enhanced_prompt = f"""You are MediBot AI, a knowledgeable medical assistant. Answer this medical question thoroughly and compassionately.

QUESTION: {query}
CATEGORY: {category}

Provide a complete response including:
- Clear explanation of the condition/topic
- Common signs and symptoms
- Typical treatments or management approaches
- Prevention tips (if applicable)
- When someone should see a doctor
- A warm, helpful follow-up question

Use simple language, bullet points, and emojis for readability. Always include a disclaimer that this is educational information.

RESPONSE:"""
            
            response = co.chat(
                message=enhanced_prompt,
                model="command-a-03-2025",
                temperature=0.7,
                max_tokens=600
            )
            
            if response and response.text:
                response_text = response.text.strip()
            else:
                response_text = get_intelligent_response(query, category)
        except Exception as e:
            print(f"AI error: {e}")
            response_text = get_intelligent_response(query, category)
    else:
        response_text = get_intelligent_response(query, category)
    
    # Save conversation
    conversations.insert_one({
        "user_id": token_data.get("user_id"),
        "session_id": request.session_id or f"session_{int(datetime.now().timestamp())}",
        "message": query,
        "response": response_text,
        "category": category,
        "timestamp": datetime.now()
    })
    
    return {"response": response_text, "timestamp": datetime.now().isoformat()}

@app.get("/category/{query}")
async def get_category(query: str):
    """API to detect category of a medical query"""
    category = detect_medical_category(query)
    is_medical = is_medical_query(query)
    return {"query": query, "is_medical": is_medical, "category": category}

@app.get("/history/{session_id}")
async def get_history(session_id: str, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"session_id": session_id, "user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1, "category": 1}
    ).sort("timestamp", 1))
    return {"history": history}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌍 MEDIBOT AI - GLOBAL MEDICAL INTELLIGENCE")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Categories: {len(MEDICAL_CATEGORIES)} medical categories")
    print(f"Coverage: ANY disease, ANY medicine, ANY symptom")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
