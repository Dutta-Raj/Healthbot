# healthbot_deepseek_style.py
"""HEALTHBOT AI WITH DEEPSEEK-STYLE RESPONSES"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, AsyncGenerator
from datetime import datetime, timedelta
import uvicorn
import os
import jwt
import bcrypt
import asyncio
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import cohere

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

SECRET_KEY = os.getenv('SECRET_KEY', 'healthbot-secret-key-2026')
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

app = FastAPI(title="HealthBot AI", version="7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_deepseek_style(text: str) -> str:
    """Format response in clean DeepSeek style"""
    if not text:
        return text
    
    # Clean up the text
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append('')
            continue
        
        # Remove markdown headers
        if line.startswith('#'):
            line = line.lstrip('#').strip()
            formatted_lines.append(f"\n**{line}**\n")
        # Format numbered lists (1. 2. 3.)
        elif re.match(r'^\d+\.', line):
            formatted_lines.append(line)
        # Format bullet points
        elif line.startswith('- ') or line.startswith('* '):
            formatted_lines.append(f"  {line}")
        else:
            formatted_lines.append(line)
    
    # Join with proper spacing
    result = '\n'.join(formatted_lines)
    
    # Add appropriate emojis based on content
    if 'blood pressure' in result.lower() or 'bp' in result.lower():
        result = "💓 **Blood Pressure Information**\n\n" + result
    elif 'headache' in result.lower():
        result = "🤕 **Headache Information**\n\n" + result
    elif 'diabetes' in result.lower():
        result = "🩸 **Diabetes Information**\n\n" + result
    elif 'fever' in result.lower():
        result = "🌡️ **Fever Information**\n\n" + result
    elif 'cold' in result.lower():
        result = "❄️ **Cold Pain Information**\n\n" + result
    
    return result

def get_deepseek_response(query: str) -> str:
    """Get DeepSeek-style structured response"""
    query_lower = query.lower()
    
    # Cold Pain Response
    if 'cold pain' in query_lower or 'cold' in query_lower:
        return """❄️ **Cold Pain - Complete Guide**

Cold pain refers to the uncomfortable or painful sensation experienced when skin or internal tissues are exposed to low temperatures. Here's a comprehensive breakdown:

---

**1. Common Examples of Cold Pain**

• **Ice cream headache** (sphenopalatine ganglioneuralgia) - Rapid cooling of the palate and throat after consuming something cold
• **Cold allodynia** - Pain from a normally non-painful cold stimulus, often seen in nerve conditions (neuropathy, post-stroke pain)
• **Frostbite pain** - Intense, throbbing pain as tissues freeze and ice crystals form
• **Raynaud's phenomenon** - Blood vessel spasms in fingers/toes when cold, causing numbness then painful rewarming

---

**2. Biological Mechanism**

Cold pain is detected by:
• **TRPM8** (menthol/cool receptor) - activated by mild cold
• **TRPA1** (pungent/cold receptor) - activated by noxious cold

These are ion channels in sensory nerve endings. Severe cold (<15°C) also:
• Directly damages cells
• Releases inflammatory mediators
• Causes ischemic pain from reduced blood flow

---

**3. Pathological Cold Pain Conditions**

| Condition | Description |
|-----------|-------------|
| Peripheral neuropathy | Diabetes, chemotherapy - cold often becomes painful |
| Central sensitization | Fibromyalgia, migraine - cold can trigger enhanced pain |
| Cold agglutinin disease | Immune-mediated pain from cold-induced blood clotting |

---

**4. Management Strategies**

1. **Avoidance & Rewarming** - Gradual, gentle heat (not direct hot water)
2. **Medications** - Gabapentin, antidepressants (TCAs/SNRIs), or topical lidocaine for neuropathy
3. **Desensitization** - Graded exposure to cold (done under supervision)

---

*Would you like me to focus on a specific condition (Raynaud's, frostbite, or neuropathic cold pain)?*

---
💡 *This information is for educational purposes. Please consult a healthcare professional for medical advice.*"""

    # Blood Pressure Response
    elif 'blood pressure' in query_lower or 'bp' in query_lower:
        return """💓 **Blood Pressure - Complete Guide**

Blood pressure is the force of blood pushing against artery walls. Here's what you need to know:

---

**1. Normal Blood Pressure Range**

| Category | Systolic (top) | Diastolic (bottom) |
|----------|---------------|-------------------|
| Normal | Less than 120 | and Less than 80 |
| Elevated | 120-129 | and Less than 80 |
| High BP Stage 1 | 130-139 | or 80-89 |
| High BP Stage 2 | 140+ | or 90+ |

---

**2. Factors Affecting Blood Pressure**

• **Diet** - High sodium intake increases BP
• **Exercise** - Regular activity lowers BP
• **Stress** - Temporary spikes during stress
• **Weight** - Obesity increases BP risk
• **Age** - BP tends to rise with age

---

**3. Tips for Healthy Blood Pressure**

1. Reduce sodium intake (less than 2300mg/day)
2. Exercise regularly (150 minutes/week)
3. Maintain healthy weight
4. Limit alcohol consumption
5. Manage stress through meditation or yoga
6. Monitor BP regularly at home

---

**4. When to See a Doctor**

• Consistent readings above 130/80
• Symptoms: severe headache, chest pain, vision changes
• Family history of hypertension

---
*Would you like specific diet recommendations or exercise plans for blood pressure management?*

---
⚠️ *This is general information. Consult your doctor for personalized medical advice.*"""

    # Headache Response
    elif 'headache' in query_lower:
        return """🤕 **Headache - Complete Guide**

Headaches are one of the most common health complaints. Here's what you should know:

---

**1. Common Types of Headaches**

| Type | Characteristics |
|------|----------------|
| **Tension** | Mild to moderate, band-like pressure around head |
| **Migraine** | Throbbing, often one-sided, with nausea/light sensitivity |
| **Cluster** | Severe burning pain around one eye |
| **Sinus** | Pressure around forehead, cheeks, eyes |

---

**2. Common Triggers**

• Dehydration - drink more water
• Eye strain - take screen breaks
• Stress and anxiety - practice relaxation
• Lack of sleep - maintain regular schedule
• Caffeine withdrawal - reduce gradually
• Certain foods (aged cheese, processed meats)

---

**3. Relief Strategies**

1. **Immediate Relief**
   - Rest in dark, quiet room
   - Apply cold or warm compress
   - Stay hydrated
   - Use OTC pain relievers (ibuprofen, acetaminophen)

2. **Long-term Prevention**
   - Identify and avoid triggers
   - Regular sleep schedule
   - Stress management techniques
   - Regular exercise

---

**4. When to See a Doctor**

• Severe, sudden "thunderclap" headache
• Headache after head injury
• Accompanied by fever, stiff neck, confusion
• Worsening pattern or frequency
• New type of headache after age 50

---
*Would you like specific guidance for migraine management or tension relief techniques?*

---
⚠️ *Seek immediate medical attention for sudden severe headaches or those following head trauma.*"""

    # Diabetes Response
    elif 'diabetes' in query_lower:
        return """🩸 **Diabetes - Complete Guide**

Diabetes affects how your body uses blood sugar. Here's comprehensive information:

---

**1. Types of Diabetes**

• **Type 1** - Body doesn't produce insulin (autoimmune)
• **Type 2** - Body doesn't use insulin properly (most common)
• **Gestational** - Develops during pregnancy

---

**2. Common Symptoms**

• Increased thirst and urination
• Unexplained weight loss
• Extreme fatigue
• Blurred vision
• Slow-healing sores
• Frequent infections

---

**3. Management Strategies**

**Lifestyle Changes:**
1. Healthy eating (focus on vegetables, whole grains, lean protein)
2. Regular exercise (150 minutes/week)
3. Weight management
4. Stress reduction

**Medical Management:**
• Monitor blood sugar regularly
• Take medications as prescribed
• Regular check-ups with endocrinologist
• Foot and eye exams annually

---

**4. Blood Sugar Targets (General)**

| Time | Target Range |
|------|-------------|
| Before meals | 80-130 mg/dL |
| After meals (2 hours) | Less than 180 mg/dL |
| A1C | Less than 7% |

---

**5. Emergency Signs**

**Hypoglycemia (Low Blood Sugar):**
• Shakiness, sweating, confusion
• Treat with 15g fast-acting carbs

**Hyperglycemia (High Blood Sugar):**
• Extreme thirst, frequent urination
• Seek medical attention if persistent

---
*Would you like specific meal planning guidance or exercise recommendations for diabetes management?*

---
⚠️ *Individual targets vary. Always follow your healthcare provider's specific recommendations.*"""

    # Default Response
    else:
        return f"""📋 **Health Information**

Thank you for your question about: *"{query[:100]}"*

---

**I can help with these health topics:**

• 💓 Blood pressure and heart health
• 🤕 Headaches and pain management  
• 🩸 Diabetes care and prevention
• 🌡️ Fever and general symptoms
• ❄️ Cold pain and temperature sensitivity
• 💊 Medication information
• 🏃‍♂️ Exercise and fitness
• 🥗 Nutrition and diet

---

**To get the best response, please:**

1. Be specific about your symptoms
2. Mention duration and severity
3. Include any relevant medical history

---

*Would you like to ask about any specific health condition?*

---
⚠️ *For medical emergencies, please call emergency services immediately.*"""

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
    return {"status": "healthy", "database": "MongoDB Atlas", "ai": "active" if co else "inactive"}

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
        "created_at": datetime.now(),
        "role": "user"
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

@app.post("/chat")
async def chat(request: ChatRequest, token_data: dict = Depends(verify_token)):
    try:
        print(f"\n💬 {token_data.get('sub')}: {request.message[:50]}...")
        
        # Get DeepSeek-style response
        response_text = get_deepseek_response(request.message)
        
        # Try to enhance with Cohere if available
        if co:
            try:
                co_response = co.chat(
                    message=f"Provide a clean, well-structured response about: {request.message}. Use numbered lists, bullet points, and clear sections. Keep it informative but concise.",
                    model="command-a-03-2025",
                    temperature=0.5,
                    max_tokens=600
                )
                if co_response and co_response.text:
                    response_text = format_deepseek_style(co_response.text)
            except:
                pass
        
        # Save conversation
        conversation = {
            "user_id": token_data.get("user_id"),
            "username": token_data.get("sub"),
            "message": request.message,
            "response": response_text,
            "timestamp": datetime.now()
        }
        conversations.insert_one(conversation)
        
        return {"response": response_text, "timestamp": datetime.now().isoformat(), "ai_used": bool(co)}
        
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/history")
async def get_history(limit: int = 50, token_data: dict = Depends(verify_token)):
    history = list(conversations.find(
        {"user_id": token_data.get("user_id")},
        {"_id": 0, "message": 1, "response": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(limit))
    return {"history": history, "count": len(history)}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏥 HEALTHBOT AI - DEEPSEEK STYLE RESPONSES")
    print("="*60)
    print(f"Server: http://localhost:8000")
    print(f"Database: MongoDB Atlas")
    print(f"AI: {'ACTIVE' if co else 'INACTIVE'}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
