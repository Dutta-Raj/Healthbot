import os
import time
import json
import jwt
import bcrypt
import requests
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, Response
from functools import wraps
from pymongo import MongoClient, errors
from bson import ObjectId
import certifi

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# --- Configuration ---
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production")
MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"

# --- Database & AI Initialization ---
chats_collection = None
users_collection = None
ai_available = False

# MongoDB Setup
try:
    client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
    client.admin.command('ismaster')
    db = client["healthq_db"]
    chats_collection = db["conversations"]
    users_collection = db["users"]
    print("✅ MongoDB connected successfully.")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    chats_collection = None
    users_collection = None

# Hugging Face API Setup with READ permissions
try:
    if HUGGINGFACE_TOKEN and HUGGINGFACE_TOKEN != "your-huggingface-token-here":
        # Test the token with a simple public API call
        headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
        test_response = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers=headers,
            timeout=10
        )
        if test_response.status_code == 200:
            user_info = test_response.json()
            ai_available = True
            print(f"✅ Hugging Face API connected successfully. Welcome {user_info.get('name', 'User')}!")
            print(f"✅ Token has READ permissions - perfect for inference!")
        else:
            print(f"❌ Hugging Face API test failed: {test_response.status_code}")
            print("Using smart local responses instead.")
            ai_available = False
    else:
        print("❌ Hugging Face token not found in environment variables")
        ai_available = False
except Exception as e:
    print(f"❌ Hugging Face initialization failed: {e}")
    print("Using smart local responses instead.")
    ai_available = False

# Enhanced health knowledge base
HEALTH_KNOWLEDGE = {
    "greetings": [
        "Hello! I'm HealthQ, your AI health assistant. I'm here to provide general health information and wellness tips. How can I help you today? 😊",
        "Hi there! I'm HealthQ, ready to discuss health and wellness topics. What would you like to know?",
        "Welcome! I'm HealthQ, your health assistant. I can help with fitness, nutrition, mental wellness, and general health questions. What's on your mind?"
    ],
    
    "symptoms": {
        "headache": "Headaches can have many causes including stress, dehydration, or tension. Try resting in a quiet room, staying hydrated, and applying a cool compress. If headaches persist or are severe, consult a doctor.",
        "fever": "Fever is often a sign your body is fighting infection. Rest, stay hydrated, and monitor your temperature. If fever is high (above 102°F/39°C) or lasts more than 3 days, see a doctor.",
        "cough": "For coughs, stay hydrated, use a humidifier, and try honey in warm water. If cough persists beyond 2 weeks or is accompanied by breathing difficulties, seek medical attention.",
        "fatigue": "Fatigue can result from poor sleep, stress, or nutritional deficiencies. Ensure you're getting 7-9 hours of sleep, eating balanced meals, and managing stress.",
        "stomach_pain": "For mild stomach discomfort, try the BRAT diet (bananas, rice, applesauce, toast) and stay hydrated. If pain is severe or persistent, consult a healthcare provider."
    },
    
    "nutrition": [
        "A balanced diet includes fruits, vegetables, whole grains, lean proteins, and healthy fats. Aim for variety and colorful plates!",
        "Stay hydrated by drinking plenty of water throughout the day. Most adults need about 8-10 cups (2-2.5 liters) daily.",
        "Limit processed foods, added sugars, and excessive salt. Focus on whole, nutrient-dense foods for optimal health.",
        "Include fiber-rich foods like fruits, vegetables, and whole grains to support digestive health.",
        "Don't skip breakfast! A balanced morning meal can help maintain energy levels throughout the day."
    ],
    
    "fitness": [
        "Aim for at least 150 minutes of moderate exercise or 75 minutes of vigorous exercise per week.",
        "Include both cardio (walking, running, swimming) and strength training exercises in your routine.",
        "Remember to warm up before exercise and cool down afterward to prevent injuries.",
        "Find activities you enjoy - you're more likely to stick with exercise you find fun!",
        "Even short bursts of activity throughout the day can contribute to your fitness goals."
    ]
}

def get_smart_local_response(user_message):
    """Generate intelligent health responses based on user input"""
    user_msg_lower = user_message.lower().strip()
    
    # Greetings
    if any(word in user_msg_lower for word in ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon']):
        return random.choice(HEALTH_KNOWLEDGE["greetings"])
    
    # Specific symptoms
    if 'headache' in user_msg_lower:
        return HEALTH_KNOWLEDGE["symptoms"]["headache"] + "\n\n⚠️ If headaches are severe or persistent, please consult a doctor."
    
    if 'fever' in user_msg_lower:
        return HEALTH_KNOWLEDGE["symptoms"]["fever"] + "\n\n🌡️ Monitor your temperature and seek medical care if concerned."
    
    if 'cough' in user_msg_lower:
        return HEALTH_KNOWLEDGE["symptoms"]["cough"] + "\n\n🤧 Persistent coughs should be evaluated by a healthcare provider."
    
    if any(word in user_msg_lower for word in ['tired', 'fatigue', 'exhausted', 'low energy']):
        return HEALTH_KNOWLEDGE["symptoms"]["fatigue"] + "\n\n💤 Quality sleep and proper nutrition can help combat fatigue."
    
    # Nutrition topics
    if any(word in user_msg_lower for word in ['diet', 'nutrition', 'food', 'eat', 'meal', 'weight']):
        response = random.choice(HEALTH_KNOWLEDGE["nutrition"])
        return f"{response}\n\n🍎 Remember: A registered dietitian can provide personalized nutrition advice."
    
    # Fitness topics
    if any(word in user_msg_lower for word in ['exercise', 'workout', 'fitness', 'gym', 'run', 'walk']):
        response = random.choice(HEALTH_KNOWLEDGE["fitness"])
        return f"{response}\n\n🏃‍♂️ Always consult with a doctor before starting new exercise programs."
    
    # Mental health topics
    if any(word in user_msg_lower for word in ['stress', 'anxiety', 'depression', 'mental', 'mood', 'worry']):
        return "🧠 Mental health is important! Practice stress management, stay connected with loved ones, and don't hesitate to seek professional support if needed. Your wellbeing matters!"
    
    # Sleep topics
    if any(word in user_msg_lower for word in ['sleep', 'insomnia', 'tired', 'rest', 'bedtime']):
        return "😴 Most adults need 7-9 hours of quality sleep. Create a consistent sleep schedule, make your bedroom comfortable, and avoid screens before bed for better rest."
    
    # Hydration
    if any(word in user_msg_lower for word in ['water', 'hydrate', 'hydration', 'thirsty', 'dehydrated']):
        return "💧 Staying hydrated is crucial! Aim for 8-10 cups of water daily. You can also get fluids from fruits, vegetables, and herbal teas."
    
    # Thank you responses
    if any(word in user_msg_lower for word in ['thank', 'thanks', 'appreciate']):
        return "You're welcome! 😊 I'm glad I could help. Remember, I'm here for general health information - always consult healthcare professionals for personal medical advice."
    
    # Help
    if 'help' in user_msg_lower:
        return "I can help with: \n• Nutrition and diet 🍎\n• Exercise and fitness 🏃‍♂️\n• Mental wellness 🧠\n• Sleep improvement 😴\n• General health information 💊\n\nWhat would you like to know about?"
    
    # Default response
    default_responses = [
        "I'm here to provide general health information. Could you tell me more about what health topic interests you?",
        "I specialize in health and wellness topics. Are you asking about nutrition, exercise, mental health, or something else?",
        "I'd love to help with your health question! Could you provide more details about what you'd like to know?"
    ]
    
    return random.choice(default_responses) + "\n\n💡 Remember: For personal medical advice, please consult a healthcare professional."

def get_huggingface_response(user_message):
    """Get response from Hugging Face using models with READ permissions"""
    try:
        # Using models that work with read permissions
        API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
        
        payload = {
            "inputs": user_message,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            },
            "options": {
                "wait_for_model": True,
                "use_cache": True
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '').strip()
                
                if generated_text and len(generated_text) > 10:
                    # Add medical disclaimer
                    return f"{generated_text}\n\n⚠️ Note: I am an AI assistant, not a doctor. Please consult a healthcare professional for medical advice."
                else:
                    return get_smart_local_response(user_message)
            else:
                return get_smart_local_response(user_message)
        else:
            print(f"Hugging Face API error: {response.status_code}")
            return get_smart_local_response(user_message)
            
    except Exception as e:
        print(f"Error calling Hugging Face API: {e}")
        return get_smart_local_response(user_message)

def get_ai_response(user_message):
    """Get the best available response"""
    if ai_available:
        try:
            return get_huggingface_response(user_message)
        except:
            return get_smart_local_response(user_message)
    else:
        return get_smart_local_response(user_message)

# --- Utility Functions for Validation ---
def validate_email(email):
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    return len(password) >= 6

def validate_name(name):
    """Validate name"""
    return len(name.strip()) >= 2

# --- Authentication Decorators ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# --- Authentication Routes ---
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()

        # Validation
        if not email or not password or not name:
            return jsonify({'error': 'All fields are required'}), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if not validate_password(password):
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        if not validate_name(name):
            return jsonify({'error': 'Name must be at least 2 characters long'}), 400

        # Check if user already exists
        if users_collection is not None:
            existing_user = users_collection.find_one({"email": email})
            if existing_user:
                return jsonify({'error': 'User already exists with this email'}), 400

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create user
        user_data = {
            "email": email,
            "password": hashed_password,
            "name": name,
            "created_at": datetime.now()
        }

        if users_collection is not None:
            result = users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
        else:
            return jsonify({'error': 'Database not available. Please try again later.'}), 500

        # Generate JWT token
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'name': name,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET, algorithm='HS256')

        return jsonify({
            'message': 'Account created successfully!',
            'token': token,
            'user_id': user_id,
            'name': name
        }), 201

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Find user
        if users_collection is not None:
            user = users_collection.find_one({"email": email})
            if not user:
                return jsonify({'error': 'Invalid email or password'}), 401

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
                return jsonify({'error': 'Invalid email or password'}), 401

            user_id = str(user['_id'])
            user_name = user.get('name', 'User')
        else:
            return jsonify({'error': 'Database not available'}), 500

        # Generate JWT token
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'name': user_name,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET, algorithm='HS256')

        return jsonify({
            'message': 'Login successful!',
            'token': token,
            'user_id': user_id,
            'name': user_name
        }), 200

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

# --- Health Check Route ---
@app.route("/health")
def health_check():
    """Health check endpoint"""
    db_status = "connected" if users_collection is not None else "disconnected"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "ai_service": "connected" if ai_available else "local_responses",
        "ai_available": ai_available,
        "timestamp": datetime.now().isoformat()
    })

# --- Debug Route ---
@app.route("/debug-db")
def debug_db():
    """Check database connection"""
    if users_collection is not None:
        try:
            user_count = users_collection.count_documents({})
            return jsonify({
                "database_status": "connected",
                "users_collection": "exists", 
                "total_users": user_count
            })
        except Exception as e:
            return jsonify({
                "database_status": "error",
                "error": str(e)
            })
    else:
        return jsonify({
            "database_status": "not_connected",
            "users_collection": "none"
        })

# --- Chat Route ---
@app.route("/chat", methods=["POST"])
@token_required
def chat(current_user):
    try:
        user_msg = request.json.get("message")
        session_id = request.json.get("session_id")

        if not user_msg:
            return jsonify({"error": "Message is required"}), 400

        # Get AI response
        response_text = get_ai_response(user_msg)

        # Save to database if available
        if chats_collection is not None:
            try:
                chat_data = {
                    "user_id": current_user,
                    "user": user_msg,
                    "bot": response_text,
                    "timestamp": datetime.now(),
                    "ai_available": ai_available
                }
                
                if session_id:
                    chats_collection.update_one(
                        {"_id": ObjectId(session_id), "user_id": current_user},
                        {"$set": chat_data}
                    )
                    result_id = session_id
                else:
                    result = chats_collection.insert_one(chat_data)
                    result_id = str(result.inserted_id)
                
                return jsonify({
                    "response": response_text,
                    "session_id": result_id
                })
            except Exception as db_error:
                print(f"Database error: {db_error}")
                return jsonify({
                    "response": response_text,
                    "session_id": session_id
                })
        else:
            return jsonify({
                "response": response_text,
                "session_id": session_id
            })

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            "response": "I apologize, but I'm having trouble responding right now. Please try again later.",
            "session_id": session_id
        })

@app.route("/history", methods=["GET"])
@token_required
def history(current_user):
    try:
        if chats_collection is not None:
            # Only get chats for this user
            chats = list(chats_collection.find(
                {"user_id": current_user}
            ).sort("timestamp", -1).limit(10))
            
            # Convert ObjectId to string for JSON serialization
            for chat in chats:
                chat['_id'] = str(chat['_id'])
                
            return jsonify(chats)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify([])

# --- Main Route with Complete HTML Template ---
@app.route("/")
def home():
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>🤖 HealthQ - AI Health Assistant</title>
      <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');
      
      :root {
          --primary: #6c63ff;
          --secondary: #4fd1c5;
          --danger: #ff6b6b;
          --text: #2d3748;
          --bg: #f8f9fa;
      }
      
      * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
      }
      
      body {
          font-family: 'Poppins', sans-serif;
          background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
          background-size: 400% 400%;
          animation: gradient 15s ease infinite;
          min-height: 100vh;
          padding: 20px;
          color: var(--text);
          display: flex;
          justify-content: center;
          align-items: center;
      }
      
      @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
      }

      /* Auth Styles */
      .auth-container {
          width: 100%;
          max-width: 400px;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 40px 30px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
      }
      
      .auth-header {
          text-align: center;
          margin-bottom: 30px;
      }
      
      .auth-header h1 {
          color: var(--primary);
          font-size: 28px;
          margin-bottom: 10px;
      }
      
      .auth-header p {
          color: #666;
          font-size: 14px;
      }
      
      .auth-tabs {
          display: flex;
          background: #f8f9fa;
          border-radius: 12px;
          padding: 4px;
          margin-bottom: 25px;
      }
      
      .auth-tab {
          flex: 1;
          padding: 12px;
          text-align: center;
          background: transparent;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s ease;
      }
      
      .auth-tab.active {
          background: var(--primary);
          color: white;
          box-shadow: 0 4px 12px rgba(108, 99, 255, 0.3);
      }
      
      .auth-form {
          display: none;
      }
      
      .auth-form.active {
          display: block;
          animation: fadeIn 0.5s ease;
      }
      
      @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
      }
      
      .auth-input-group {
          margin-bottom: 20px;
      }
      
      .auth-input {
          width: 100%;
          padding: 15px;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          font-size: 16px;
          transition: all 0.3s ease;
          background: white;
      }
      
      .auth-input:focus {
          outline: none;
          border-color: var(--primary);
          box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.1);
      }
      
      .auth-btn {
          width: 100%;
          padding: 15px;
          background: var(--primary);
          color: white;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          font-size: 16px;
          font-weight: 600;
          transition: all 0.3s ease;
          margin-top: 10px;
      }
      
      .auth-btn:hover {
          background: #5a52e0;
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(108, 99, 255, 0.3);
      }
      
      .auth-btn:active {
          transform: translateY(0);
      }
      
      .error-message {
          background: #fed7d7;
          color: #c53030;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 20px;
          font-size: 14px;
          display: none;
      }
      
      .success-message {
          background: #c6f6d5;
          color: #276749;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 20px;
          font-size: 14px;
          display: none;
      }
      
      .chat-interface {
          display: none;
          width: 100%;
          max-width: 1400px;
          height: 90vh;
      }
      
      .user-info {
          position: absolute;
          top: 20px;
          right: 20px;
          color: white;
          background: rgba(0,0,0,0.5);
          padding: 10px 20px;
          border-radius: 25px;
          font-size: 14px;
          z-index: 1000;
      }

      /* Chat Interface Styles */
      .chat-layout {
          display: flex;
          width: 100%;
          height: 100%;
          gap: 20px;
      }
      
      /* Sidebar Styles */
      .sidebar {
          width: 300px;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 20px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          flex-direction: column;
      }
      
      .sidebar-header {
          margin-bottom: 20px;
      }
      
      .new-chat-btn {
          width: 100%;
          padding: 12px;
          background: var(--primary);
          color: white;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.3s ease;
          margin-bottom: 20px;
      }
      
      .new-chat-btn:hover {
          background: #5a52e0;
          transform: translateY(-2px);
      }
      
      .chat-history {
          flex: 1;
          overflow-y: auto;
      }
      
      .chat-history-item {
          padding: 12px;
          margin-bottom: 8px;
          background: #f8f9fa;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s ease;
          border: 1px solid transparent;
      }
      
      .chat-history-item:hover {
          background: #e9ecef;
          border-color: var(--primary);
      }
      
      .chat-history-item.active {
          background: var(--primary);
          color: white;
      }
      
      .chat-preview {
          font-size: 12px;
          color: #666;
          margin-top: 4px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
      }
      
      .chat-history-item.active .chat-preview {
          color: rgba(255,255,255,0.8);
      }
      
      .chat-date {
          font-size: 10px;
          color: #999;
          margin-top: 4px;
      }
      
      .chat-history-item.active .chat-date {
          color: rgba(255,255,255,0.6);
      }
      
      /* Main Chat Container */
      .chat-container {
          flex: 1;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 40px rgba(0,0,0,0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          overflow: hidden;
      }
      
      .chat-header {
          background: var(--primary);
          color: white;
          padding: 20px;
          text-align: center;
          border-radius: 20px 20px 0 0;
      }
      
      .chat-header h2 {
          margin: 0;
          font-size: 24px;
      }
      
      .chat-messages {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          background: #f8f9fa;
          scroll-behavior: smooth;
      }
      
      .chat-messages::-webkit-scrollbar {
          width: 6px;
      }
      
      .chat-messages::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 3px;
      }
      
      .chat-messages::-webkit-scrollbar-thumb {
          background: #c1c1c1;
          border-radius: 3px;
      }
      
      .chat-messages::-webkit-scrollbar-thumb:hover {
          background: #a8a8a8;
      }
      
      .message {
          margin-bottom: 15px;
          padding: 12px 16px;
          border-radius: 18px;
          max-width: 70%;
          word-wrap: break-word;
          animation: fadeIn 0.3s ease;
      }
      
      .user-message {
          background: var(--primary);
          color: white;
          margin-left: auto;
          border-bottom-right-radius: 4px;
      }
      
      .bot-message {
          background: white;
          color: var(--text);
          border: 1px solid #e2e8f0;
          margin-right: auto;
          border-bottom-left-radius: 4px;
      }
      
      .chat-input-container {
          padding: 20px;
          border-top: 1px solid #e2e8f0;
          background: white;
      }
      
      .chat-input-wrapper {
          display: flex;
          gap: 10px;
          align-items: center;
      }
      
      .chat-input {
          flex: 1;
          padding: 15px;
          border: 2px solid #e2e8f0;
          border-radius: 25px;
          font-size: 16px;
          outline: none;
          transition: border-color 0.3s ease;
      }
      
      .chat-input:focus {
          border-color: var(--primary);
      }
      
      .mic-button {
          background: #4fd1c5;
          color: white;
          border: none;
          border-radius: 50%;
          width: 50px;
          height: 50px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          font-size: 18px;
      }
      
      .mic-button:hover {
          background: #38b2ac;
          transform: scale(1.05);
      }
      
      .mic-button.recording {
          background: var(--danger);
          animation: pulse 1.5s infinite;
      }
      
      .stop-button {
          background: var(--danger);
          color: white;
          border: none;
          border-radius: 50%;
          width: 50px;
          height: 50px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          font-size: 18px;
          display: none;
      }
      
      .stop-button:hover {
          background: #e53e3e;
          transform: scale(1.05);
      }
      
      .send-button {
          background: var(--primary);
          color: white;
          border: none;
          border-radius: 50%;
          width: 50px;
          height: 50px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          font-size: 18px;
      }
      
      .send-button:hover {
          background: #5a52e0;
          transform: scale(1.05);
      }
      
      .send-button:disabled {
          background: #ccc;
          cursor: not-allowed;
          transform: none;
      }
      
      .typing-indicator {
          display: none;
          padding: 12px 16px;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 18px;
          margin-right: auto;
          max-width: 70%;
          border-bottom-left-radius: 4px;
          color: #666;
          font-style: italic;
      }
      
      .disclaimer {
          font-size: 12px;
          color: #666;
          text-align: center;
          padding: 10px;
          background: #f1f3f4;
          border-radius: 10px;
          margin-top: 10px;
      }
      
      @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.1); }
          100% { transform: scale(1); }
      }
      
      .empty-state {
          text-align: center;
          color: #666;
          padding: 40px 20px;
      }
      
      .empty-state i {
          font-size: 48px;
          margin-bottom: 10px;
          opacity: 0.5;
      }

      .ai-status {
          padding: 8px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
          margin-top: 10px;
          text-align: center;
      }
      
      .ai-status.connected {
          background: #c6f6d5;
          color: #276749;
      }
      
      .ai-status.disconnected {
          background: #fed7d7;
          color: #c53030;
      }
      </style>
    </head>
    <body>
      <!-- Authentication Interface -->
      <div id="authInterface" class="auth-container">
        <div class="auth-header">
          <h1>🤖 HealthQ</h1>
          <p>AI Health Assistant - Secure Login</p>
        </div>
        
        <div class="error-message" id="errorMessage"></div>
        <div class="success-message" id="successMessage"></div>
        
        <div class="auth-tabs">
          <button class="auth-tab active" onclick="showAuthForm('login')">Login</button>
          <button class="auth-tab" onclick="showAuthForm('register')">Create Account</button>
        </div>
        
        <div id="loginForm" class="auth-form active">
          <div class="auth-input-group">
            <input type="email" id="loginEmail" class="auth-input" placeholder="Enter your email" required>
          </div>
          <div class="auth-input-group">
            <input type="password" id="loginPassword" class="auth-input" placeholder="Enter your password" required>
          </div>
          <button class="auth-btn" onclick="handleLogin()">Login to HealthQ</button>
        </div>
        
        <div id="registerForm" class="auth-form">
          <div class="auth-input-group">
            <input type="text" id="registerName" class="auth-input" placeholder="Full name" required>
          </div>
          <div class="auth-input-group">
            <input type="email" id="registerEmail" class="auth-input" placeholder="Email address" required>
          </div>
          <div class="auth-input-group">
            <input type="password" id="registerPassword" class="auth-input" placeholder="Create password" required>
          </div>
          <button class="auth-btn" onclick="handleRegister()">Create Account</button>
        </div>
      </div>

      <!-- Chat Interface (Hidden initially) -->
      <div id="chatInterface" class="chat-interface">
        <div class="user-info" id="userInfo">
          Welcome! • <a href="#" onclick="handleLogout()" style="color: white; margin-left: 10px;">Logout</a>
        </div>
        
        <!-- Chat Layout with Sidebar -->
        <div class="chat-layout">
          <!-- Sidebar for Chat History -->
          <div class="sidebar">
            <div class="sidebar-header">
              <button class="new-chat-btn" onclick="createNewChat()">
                ＋ New Chat
              </button>
              <div id="aiStatus" class="ai-status disconnected">
                AI: Connecting...
              </div>
            </div>
            <div class="chat-history" id="chatHistory">
              <!-- Chat history will be loaded here -->
            </div>
          </div>
          
          <!-- Main Chat Area -->
          <div id="chatAppContainer"></div>
        </div>
      </div>

      <script>
        let authToken = null;
        let currentUserId = null;
        let currentUserName = null;
        let currentSessionId = null;
        let isRecording = false;
        let recognition = null;
        let aiAvailable = false;

        // Check AI status on load
        async function checkAIStatus() {
          try {
            const response = await fetch('/health');
            const data = await response.json();
            aiAvailable = data.ai_available;
            
            const aiStatus = document.getElementById('aiStatus');
            if (aiAvailable) {
              aiStatus.textContent = 'AI: Connected ✓';
              aiStatus.className = 'ai-status connected';
            } else {
              aiStatus.textContent = 'AI: Using Local Mode';
              aiStatus.className = 'ai-status disconnected';
            }
          } catch (error) {
            console.error('Error checking AI status:', error);
          }
        }

        // Initialize speech recognition
        function initSpeechRecognition() {
          if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = function() {
              isRecording = true;
              updateRecordingUI();
            };

            recognition.onresult = function(event) {
              const transcript = event.results[0][0].transcript;
              document.getElementById('userInput').value = transcript;
            };

            recognition.onerror = function(event) {
              console.error('Speech recognition error', event.error);
              stopRecording();
            };

            recognition.onend = function() {
              stopRecording();
            };
          } else {
            console.log('Speech recognition not supported');
          }
        }

        function startRecording() {
          if (recognition) {
            recognition.start();
          }
        }

        function stopRecording() {
          if (recognition) {
            recognition.stop();
            isRecording = false;
            updateRecordingUI();
          }
        }

        function updateRecordingUI() {
          const micButton = document.getElementById('micButton');
          const stopButton = document.getElementById('stopButton');
          
          if (isRecording) {
            micButton.style.display = 'none';
            stopButton.style.display = 'flex';
          } else {
            micButton.style.display = 'flex';
            stopButton.style.display = 'none';
          }
        }

        // Show auth form function
        function showAuthForm(formType) {
          // Update tabs
          document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.classList.remove('active');
          });
          event.target.classList.add('active');
          
          // Update forms
          document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.remove('active');
          });
          document.getElementById(formType + 'Form').classList.add('active');
          
          // Clear messages
          hideMessages();
        }

        // Hide all messages
        function hideMessages() {
          document.getElementById('errorMessage').style.display = 'none';
          document.getElementById('successMessage').style.display = 'none';
        }

        // Show error message
        function showError(message) {
          const errorDiv = document.getElementById('errorMessage');
          errorDiv.textContent = message;
          errorDiv.style.display = 'block';
          document.getElementById('successMessage').style.display = 'none';
        }

        // Show success message
        function showSuccess(message) {
          const successDiv = document.getElementById('successMessage');
          successDiv.textContent = message;
          successDiv.style.display = 'block';
          document.getElementById('errorMessage').style.display = 'none';
        }

        // Handle login
        async function handleLogin() {
          const email = document.getElementById('loginEmail').value.trim();
          const password = document.getElementById('loginPassword').value.trim();

          if (!email || !password) {
            showError('Please fill in all fields');
            return;
          }

          try {
            const response = await fetch('/login', {
              method: 'POST',
              headers: { 
                'Content-Type': 'application/json' 
              },
              body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            
            if (response.ok) {
              authToken = data.token;
              currentUserId = data.user_id;
              currentUserName = data.name;
              showChatInterface();
              showSuccess('Login successful! Welcome back!');
            } else {
              showError(data.error || 'Login failed');
            }
          } catch (error) {
            showError('Network error. Please try again.');
          }
        }

        // Handle register
        async function handleRegister() {
          const name = document.getElementById('registerName').value.trim();
          const email = document.getElementById('registerEmail').value.trim();
          const password = document.getElementById('registerPassword').value.trim();

          if (!name || !email || !password) {
            showError('Please fill in all fields');
            return;
          }

          if (password.length < 6) {
            showError('Password must be at least 6 characters long');
            return;
          }

          try {
            const response = await fetch('/register', {
              method: 'POST',
              headers: { 
                'Content-Type': 'application/json' 
              },
              body: JSON.stringify({ name, email, password })
            });

            const data = await response.json();
            
            if (response.ok) {
              showSuccess('Account created successfully! Please login.');
              // Switch to login form after successful registration
              setTimeout(() => {
                showAuthForm('login');
                document.getElementById('loginEmail').value = email;
              }, 2000);
            } else {
              showError(data.error || 'Registration failed');
            }
          } catch (error) {
            showError('Network error. Please try again.');
          }
        }

        // Show chat interface
        function showChatInterface() {
          document.getElementById('authInterface').style.display = 'none';
          document.getElementById('chatInterface').style.display = 'block';
          document.getElementById('userInfo').innerHTML = 
            `Welcome, ${currentUserName}! • <a href="#" onclick="handleLogout()" style="color: white; margin-left: 10px;">Logout</a>`;
          
          // Load chat history and initialize chat
          loadChatHistory();
          createNewChat();
          checkAIStatus();
        }

        // Load chat history
        async function loadChatHistory() {
          try {
            const response = await fetch('/history', {
              method: 'GET',
              headers: {
                'Authorization': `Bearer ${authToken}`
              }
            });

            if (response.ok) {
              const chats = await response.json();
              displayChatHistory(chats);
            }
          } catch (error) {
            console.error('Error loading chat history:', error);
          }
        }

        // Display chat history in sidebar
        function displayChatHistory(chats) {
          const chatHistory = document.getElementById('chatHistory');
          
          if (chats.length === 0) {
            chatHistory.innerHTML = `
              <div class="empty-state">
                <div>💬</div>
                <p>No previous chats</p>
                <p style="font-size: 12px; margin-top: 5px;">Start a new conversation!</p>
              </div>
            `;
            return;
          }

          chatHistory.innerHTML = chats.map(chat => `
            <div class="chat-history-item ${chat._id === currentSessionId ? 'active' : ''}" 
                 onclick="loadChat('${chat._id}')">
              <div style="font-weight: 500;">
                ${chat.user ? chat.user.substring(0, 30) + (chat.user.length > 30 ? '...' : '') : 'New Chat'}
              </div>
              <div class="chat-preview">
                ${chat.bot ? chat.bot.substring(0, 50) + (chat.bot.length > 50 ? '...' : '') : 'No response yet'}
              </div>
              <div class="chat-date">
                ${new Date(chat.timestamp).toLocaleDateString()} • ${new Date(chat.timestamp).toLocaleTimeString()}
              </div>
            </div>
          `).join('');
        }

        // Create new chat
        function createNewChat() {
          currentSessionId = null;
          loadChatApp();
          updateActiveChatInSidebar();
        }

        // Load specific chat
        function loadChat(chatId) {
          currentSessionId = chatId;
          // In a real app, you would fetch the specific chat messages
          // For now, we'll just update the UI and clear current messages
          loadChatApp();
          updateActiveChatInSidebar();
        }

        // Update active chat in sidebar
        function updateActiveChatInSidebar() {
          document.querySelectorAll('.chat-history-item').forEach(item => {
            item.classList.remove('active');
          });
          
          if (currentSessionId) {
            const activeItem = document.querySelector(`[onclick="loadChat('${currentSessionId}')"]`);
            if (activeItem) {
              activeItem.classList.add('active');
            }
          }
        }

        // Load the main chat application
        function loadChatApp() {
          document.getElementById('chatAppContainer').innerHTML = `
            <div class="chat-container">
                <div class="chat-header">
                    <h2>🤖 HealthQ AI Assistant</h2>
                    <p>Ask me anything about health and wellness</p>
                </div>
                
                <div class="chat-messages" id="chatMessages">
                    <div class="message bot-message">
                        ${currentSessionId ? 'Continuing previous conversation...' : `Hello ${currentUserName}! I'm HealthQ, your AI health assistant. How can I help you today? 😊`}
                        ${!aiAvailable ? '<br><br><small>⚠️ Note: Currently using local health knowledge base.</small>' : ''}
                    </div>
                </div>
                
                <div class="typing-indicator" id="typingIndicator">
                    HealthQ is typing...
                </div>
                
                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <input 
                            type="text" 
                            class="chat-input" 
                            id="userInput" 
                            placeholder="Type your health question here..."
                            maxlength="500"
                        >
                        <button class="mic-button" id="micButton" onclick="startRecording()">
                            🎤
                        </button>
                        <button class="stop-button" id="stopButton" onclick="stopRecording()">
                            ⏹️
                        </button>
                        <button class="send-button" onclick="sendMessage()" id="sendButton">
                            ➤
                        </button>
                    </div>
                    <div class="disclaimer">
                        ⚠️ Remember: I'm an AI assistant, not a doctor. For serious medical concerns, please consult a healthcare professional.
                    </div>
                </div>
            </div>
          `;

          // Initialize speech recognition
          initSpeechRecognition();

          // Add event listeners for the new chat interface
          setTimeout(() => {
              const userInput = document.getElementById('userInput');
              const sendButton = document.getElementById('sendButton');
              
              userInput.addEventListener('keypress', function(e) {
                  if (e.key === 'Enter') {
                      sendMessage();
                  }
              });
              
              userInput.focus();
          }, 100);
        }

        // Send message to chatbot
        async function sendMessage() {
            const userInput = document.getElementById('userInput');
            const sendButton = document.getElementById('sendButton');
            const chatMessages = document.getElementById('chatMessages');
            const typingIndicator = document.getElementById('typingIndicator');
            
            const message = userInput.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user-message';
            userMessageDiv.textContent = message;
            chatMessages.appendChild(userMessageDiv);
            
            // Clear input and disable button
            userInput.value = '';
            sendButton.disabled = true;
            
            // Show typing indicator
            typingIndicator.style.display = 'block';
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: currentSessionId
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                
                // Hide typing indicator
                typingIndicator.style.display = 'none';
                
                // Add bot message to chat
                const botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'message bot-message';
                botMessageDiv.textContent = data.response;
                chatMessages.appendChild(botMessageDiv);
                
                // Update session ID if provided
                if (data.session_id) {
                    currentSessionId = data.session_id;
                    loadChatHistory();
                }
                
            } catch (error) {
                console.error('Error:', error);
                typingIndicator.style.display = 'none';
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-message';
                errorDiv.textContent = 'Sorry, I encountered an error. Please try again.';
                chatMessages.appendChild(errorDiv);
            } finally {
                sendButton.disabled = false;
                userInput.focus();
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }

        // Handle logout
        function handleLogout() {
          authToken = null;
          currentUserId = null;
          currentUserName = null;
          currentSessionId = null;
          document.getElementById('authInterface').style.display = 'block';
          document.getElementById('chatInterface').style.display = 'none';
          hideMessages();
          showAuthForm('login');
        }

        // Enter key support
        document.addEventListener('DOMContentLoaded', function() {
          // Login form enter key
          document.getElementById('loginPassword').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
              handleLogin();
            }
          });

          // Register form enter key
          document.getElementById('registerPassword').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
              handleRegister();
            }
          });
        });
      </script>
    </body>
    </html>
    """
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
