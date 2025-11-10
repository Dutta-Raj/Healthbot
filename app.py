import os
import jwt
import uuid
import json
import re
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from dotenv import load_dotenv
from bcrypt import hashpw, gensalt, checkpw
from kafka import KafkaProducer, KafkaConsumer

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-2024')

# Simple Health Response System (NO API DEPENDENCY)
def get_health_response(user_message):
    """Simple working health responses without external API"""
    user_lower = user_message.lower()
    
    # Pattern matching for common health questions
    if any(word in user_lower for word in ['exercise', 'fitness', 'workout', 'gym']):
        return "For exercise and fitness, I recommend starting with 30 minutes of moderate activity daily like walking, cycling, or swimming. Remember to warm up, stay hydrated, and consult your doctor before starting any new exercise routine."
    
    elif any(word in user_lower for word in ['diet', 'nutrition', 'food', 'eat', 'weight']):
        return "A balanced diet includes plenty of fruits, vegetables, whole grains, and lean proteins. Stay hydrated with water and limit processed foods. For personalized nutrition advice, consult a registered dietitian."
    
    elif any(word in user_lower for word in ['sleep', 'insomnia', 'tired', 'energy']):
        return "Good sleep habits include maintaining a consistent schedule (7-9 hours nightly), creating a dark/quiet bedroom, avoiding screens before bed, and limiting caffeine in the evening. If sleep problems persist, see a healthcare provider."
    
    elif any(word in user_lower for word in ['cold', 'flu', 'fever', 'cough', 'sick']):
        return "For cold and flu symptoms: rest, drink plenty of fluids, use over-the-counter remedies as needed. Seek medical attention for high fever, difficulty breathing, or symptoms lasting more than 10 days."
    
    elif any(word in user_lower for word in ['stress', 'anxiety', 'mental', 'mood']):
        return "For stress management: practice deep breathing, regular exercise, maintain social connections, and ensure adequate sleep. Consider speaking with a mental health professional for persistent concerns."
    
    elif any(word in user_lower for word in ['headache', 'pain']):
        return "For occasional headaches: rest in a quiet/dark room, stay hydrated, and consider over-the-counter pain relief. Consult a doctor for severe, frequent, or worsening headaches."
    
    elif any(word in user_lower for word in ['skin', 'acne', 'rash']):
        return "Basic skin care includes gentle cleansing, moisturizing, and sun protection. For specific skin concerns like persistent acne or rashes, consult a dermatologist."
    
    elif any(word in user_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "Hello! I'm your health assistant. I can help with general wellness topics like exercise, nutrition, sleep, and common health questions. How can I assist you today?"
    
    elif any(word in user_lower for word in ['thank', 'thanks', 'appreciate']):
        return "You're welcome! I'm glad I could help. Remember to consult healthcare professionals for specific medical concerns."
    
    else:
        return "I'm here to help with general health and wellness information. I can provide guidance on exercise, nutrition, sleep, stress management, and common health topics. For specific medical concerns, please consult a healthcare professional."

print("✅ Health response system initialized successfully!")

# Validation functions
def validate_email(email):
    """Validate email format with better error handling"""
    if not email or not isinstance(email, str):
        return False, "Email is required"
    
    email = email.strip()
    
    # Basic email format check
    if '@' not in email:
        return False, "Email must contain @ symbol"
    
    if '.' not in email:
        return False, "Email must contain a domain with dot"
    
    if len(email) < 5:
        return False, "Email is too short"
    
    if len(email) > 254:
        return False, "Email is too long"
    
    # Split and check parts
    parts = email.split('@')
    if len(parts) != 2:
        return False, "Email must contain exactly one @ symbol"
    
    local_part, domain = parts
    
    if len(local_part) == 0:
        return False, "Local part (before @) cannot be empty"
    
    if len(domain) == 0:
        return False, "Domain part (after @) cannot be empty"
    
    if '.' not in domain:
        return False, "Domain must contain a dot"
    
    # Check for common invalid patterns
    if '..' in email:
        return False, "Email cannot contain consecutive dots"
    
    if email.startswith('.') or email.endswith('.'):
        return False, "Email cannot start or end with a dot"
    
    if email.startswith('@') or email.endswith('@'):
        return False, "Email cannot start or end with @"
    
    # Check for valid characters (simplified regex)
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Email format is invalid"
    
    return True, email

def validate_password(password):
    """Validate password strength"""
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_name(name):
    """Validate name format"""
    if not name or not isinstance(name, str):
        return False, "Name is required"
    
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long"
    
    if len(name) > 50:
        return False, "Name must be less than 50 characters"
    
    # Check if name contains only letters, spaces, and basic punctuation
    if not re.match(r'^[a-zA-Z\s\-\'\.]+$', name):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"
    
    return True, name.strip()

def validate_medical_content(message):
    """Validate that the message doesn't contain emergency or dangerous content"""
    if not message or not isinstance(message, str):
        return True, ""  # Empty message will be handled elsewhere
    
    message_lower = message.lower()
    
    # Emergency keywords that should trigger immediate professional help recommendation
    emergency_keywords = [
        'heart attack', 'chest pain', 'stroke', 'suicide', 'kill myself',
        'dying', 'severe pain', 'can\'t breathe', 'difficulty breathing',
        'unconscious', 'bleeding heavily', 'broken bone', 'seizure',
        'overdose', 'poison', 'burn', 'electrocution'
    ]
    
    for keyword in emergency_keywords:
        if keyword in message_lower:
            return False, f"Emergency situation detected: {keyword}. Please call emergency services immediately."
    
    return True, ""

# Medical Disclaimer
MEDICAL_DISCLAIMER = """**Important Medical Disclaimer**: 
I am an AI assistant and not a medical professional. My advice is for informational purposes only and should not be considered medical advice. Always consult with a qualified healthcare provider for medical concerns, diagnoses, or treatment. In case of emergency, contact emergency services immediately."""

# MongoDB Configuration
try:
    mongo_uri = os.getenv('MONGO_URI') or f"mongodb+srv://{os.getenv('MONGO_USERNAME')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_CLUSTER')}/{os.getenv('MONGO_DB_NAME')}?retryWrites=true&w=majority"
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    db = client[os.getenv('MONGO_DB_NAME', 'healthbot')]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    # Fallback to local database or create mock
    client, db = None, None

# Kafka Configuration
KAFKA_ENABLED = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

kafka_producer = None
if KAFKA_ENABLED:
    try:
        kafka_producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda v: v.encode('utf-8') if v else None
        )
        print("✅ Kafka producer connected successfully!")
    except Exception as e:
        print(f"❌ Kafka connection failed: {e}")
        KAFKA_ENABLED = False

# Initialize Database
def init_database():
    if db is None:
        return
    
    try:
        collections = ['users', 'conversations', 'message_logs', 'chat_sessions']
        existing_collections = db.list_collection_names()
        
        for collection_name in collections:
            if collection_name not in existing_collections:
                db.create_collection(collection_name)
                print(f"✅ Created collection: {collection_name}")
        
        db.users.create_index([("email", 1)], unique=True)
        db.conversations.create_index([("user_id", 1), ("timestamp", -1)])
        db.conversations.create_index([("session_id", 1)])
        db.chat_sessions.create_index([("user_id", 1), ("created_at", -1)])
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

init_database()

# Authentication Middleware
def token_required(f):
    def decorated(*args, **kwargs):
        if db is None:
            return jsonify({"error": "Database connection unavailable"}), 503
            
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, os.getenv('JWT_SECRET', 'secret'), algorithms=["HS256"])
            current_user = db.users.find_one({"user_id": data['user_id']})
            if not current_user:
                return jsonify({"error": "User not found"}), 401
            request.current_user = current_user
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# Kafka Message Producer
def send_kafka_message(topic, message, key=None):
    if KAFKA_ENABLED and kafka_producer:
        try:
            kafka_producer.send(topic, value=message, key=key)
            kafka_producer.flush()
        except Exception as e:
            print(f"❌ Kafka message sending failed: {e}")

# Kafka Consumer
def start_kafka_consumer():
    if not KAFKA_ENABLED:
        return
    
    def consume_messages():
        try:
            consumer = KafkaConsumer(
                'chat_messages',
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='chatbot_group',
                auto_offset_reset='earliest'
            )
            
            for message in consumer:
                process_kafka_message(message.value)
                
        except Exception as e:
            print(f"❌ Kafka consumer error: {e}")
    
    consumer_thread = threading.Thread(target=consume_messages, daemon=True)
    consumer_thread.start()

def process_kafka_message(message):
    try:
        print(f"📨 Processing Kafka message: {message}")
        if db is not None:
            db.message_logs.insert_one({
                **message,
                'processed_at': datetime.utcnow()
            })
    except Exception as e:
        print(f"❌ Error processing Kafka message: {e}")

# Start Kafka consumer
start_kafka_consumer()

# Helper function to get or create current session
def get_current_session(user_id):
    if db is None:
        return str(uuid.uuid4())
    
    # Get today's session or create new one
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    session = db.chat_sessions.find_one({
        "user_id": user_id,
        "created_at": {"$gte": today_start, "$lt": today_end}
    })
    
    if not session:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "message_count": 0,
            "last_activity": datetime.utcnow()
        }
        db.chat_sessions.insert_one(session_data)
        return session_id
    
    # Update last activity
    db.chat_sessions.update_one(
        {"session_id": session["session_id"]},
        {"$set": {"last_activity": datetime.utcnow()}}
    )
    
    return session["session_id"]

# Frontend Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATES['index'])

@app.route('/login')
def login_page():
    return render_template_string(HTML_TEMPLATES['login'])

@app.route('/register')
def register_page():
    return render_template_string(HTML_TEMPLATES['register'])

@app.route('/chat')
def chat_page():
    return render_template_string(HTML_TEMPLATES['chat'])

@app.route('/profile')
def profile_page():
    return render_template_string(HTML_TEMPLATES['profile'])

# Backend API Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    if db is None:
        return jsonify({"error": "Database connection unavailable"}), 503
        
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        # Validate inputs
        if not email or not password or not name:
            return jsonify({"error": "Email, password, and name are required"}), 400
        
        # Validate email
        is_valid_email, email_message = validate_email(email)
        if not is_valid_email:
            return jsonify({"error": email_message}), 400
        
        # Validate password
        is_valid_password, password_message = validate_password(password)
        if not is_valid_password:
            return jsonify({"error": password_message}), 400
        
        # Validate name
        is_valid_name, name_message = validate_name(name)
        if not is_valid_name:
            return jsonify({"error": name_message}), 400
        
        if db.users.find_one({"email": email}):
            return jsonify({"error": "User already exists"}), 400
        
        hashed_password = hashpw(password.encode('utf-8'), gensalt())
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password": hashed_password.decode('utf-8'),
            "name": name,
            "created_at": datetime.utcnow(),
        }
        
        db.users.insert_one(user_data)
        
        token = jwt.encode({
            'user_id': user_data['user_id'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }, os.getenv('JWT_SECRET', 'secret'), algorithm="HS256")
        
        send_kafka_message('user_events', {
            'event_type': 'user_registered',
            'user_id': user_data['user_id'],
            'email': email,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user_id": user_data['user_id'],
            "name": name
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    if db is None:
        return jsonify({"error": "Database connection unavailable"}), 503
        
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        user = db.users.find_one({"email": email})
        if not user or not checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({"error": "Invalid credentials"}), 401
        
        token = jwt.encode({
            'user_id': user['user_id'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }, os.getenv('JWT_SECRET', 'secret'), algorithm="HS256")
        
        send_kafka_message('user_events', {
            'event_type': 'user_logged_in',
            'user_id': user['user_id'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user_id": user['user_id'],
            "name": user.get('name')
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# UPDATED CHAT ROUTE WITH SIMPLE RESPONSE SYSTEM
@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Validate medical content for emergencies
        is_safe, emergency_message = validate_medical_content(user_message)
        if not is_safe:
            return jsonify({
                "response": f"🚨 {emergency_message} Please call emergency services immediately.",
                "session_id": session_id or get_current_session(request.current_user['user_id'])
            })
        
        # Get or create session
        if not session_id:
            session_id = get_current_session(request.current_user['user_id'])
        
        # Get response from simple health system (NO API DEPENDENCY)
        bot_response = get_health_response(user_message)
        
        # Add disclaimer for medical topics
        medical_keywords = ['symptom', 'pain', 'fever', 'headache', 'cough', 'cold', 'flu', 'disease', 'condition', 'diagnose', 'treatment', 'medicine', 'drug', 'pill']
        if any(keyword in user_message.lower() for keyword in medical_keywords):
            bot_response += f"\n\n{MEDICAL_DISCLAIMER}"
        
        # Save conversation
        conversation_data = {
            'conversation_id': str(uuid.uuid4()),
            'session_id': session_id,
            'user_id': request.current_user['user_id'],
            'user_message': user_message,
            'bot_response': bot_response,
            'timestamp': datetime.utcnow()
        }

        if db is not None:
            db.conversations.insert_one(conversation_data)
            
            # Update session
            db.chat_sessions.update_one(
                {"session_id": session_id},
                {
                    "$inc": {"message_count": 1},
                    "$set": {
                        "last_activity": datetime.utcnow(),
                        "user_id": request.current_user['user_id']
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        
        # Send to Kafka if enabled
        send_kafka_message('chat_messages', {
            'conversation_id': conversation_data['conversation_id'],
            'user_id': request.current_user['user_id'],
            'user_message': user_message,
            'bot_response': bot_response,
            'timestamp': conversation_data['timestamp'].isoformat()
        })
        
        return jsonify({
            "response": bot_response,
            "conversation_id": conversation_data['conversation_id'],
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"Chat API error: {e}")
        return jsonify({"error": "Sorry, I'm having trouble processing your request. Please try again."}), 500

@app.route('/api/chat/history', methods=['GET'])
@token_required
def get_chat_history():
    try:
        days = int(request.args.get('days', 30))
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get chat sessions with proper grouping
        pipeline = [
            {"$match": {
                "user_id": request.current_user['user_id'],
                "timestamp": {"$gte": since_date}
            }},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$session_id",
                "last_message": {"$first": "$user_message"},
                "message_count": {"$sum": 1},
                "last_timestamp": {"$first": "$timestamp"},
                "first_timestamp": {"$min": "$timestamp"}
            }},
            {"$sort": {"last_timestamp": -1}},
            {"$project": {
                "session_id": "$_id",
                "preview": {"$cond": {
                    "if": {"$gt": [{"$strLenCP": "$last_message"}, 50]},
                    "then": {"$concat": [{"$substrCP": ["$last_message", 0, 47]}, "..."]},
                    "else": "$last_message"
                }},
                "message_count": 1,
                "date": "$last_timestamp",
                "_id": 0
            }}
        ]
        
        sessions = list(db.conversations.aggregate(pipeline)) if db is not None else []
        
        return jsonify({"sessions": sessions})
    except Exception as e:
        print(f"Chat history error: {e}")
        return jsonify({"sessions": []})

@app.route('/api/chat/session/<session_id>', methods=['GET'])
@token_required
def get_chat_session(session_id):
    try:
        conversations = list(db.conversations.find(
            {
                'user_id': request.current_user['user_id'],
                'session_id': session_id
            },
            {'_id': 0, 'user_message': 1, 'bot_response': 1, 'timestamp': 1}
        ).sort('timestamp', 1)) if db is not None else []
        
        # Format messages for display
        messages = []
        for conv in conversations:
            messages.extend([
                {
                    'sender': 'user',
                    'text': conv['user_message'],
                    'timestamp': conv['timestamp']
                },
                {
                    'sender': 'bot', 
                    'text': conv['bot_response'],
                    'timestamp': conv['timestamp']
                }
            ])
        
        return jsonify({
            "messages": messages, 
            "session_id": session_id,
            "count": len(messages)
        })
    except Exception as e:
        print(f"Chat session error: {e}")
        return jsonify({"messages": [], "session_id": session_id})

@app.route('/api/chat/current', methods=['GET'])
@token_required
def get_current_chat():
    try:
        session_id = get_current_session(request.current_user['user_id'])
        
        # Get today's messages
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        conversations = list(db.conversations.find(
            {
                'user_id': request.current_user['user_id'],
                'session_id': session_id,
                'timestamp': {"$gte": today_start}
            },
            {'_id': 0, 'user_message': 1, 'bot_response': 1, 'timestamp': 1}
        ).sort('timestamp', 1)) if db is not None else []
        
        # Format messages for display
        messages = []
        for conv in conversations:
            messages.append({
                'sender': 'user',
                'text': conv['user_message'],
                'timestamp': conv['timestamp']
            })
            messages.append({
                'sender': 'bot',
                'text': conv['bot_response'],
                'timestamp': conv['timestamp']
            })
        
        return jsonify({"messages": messages, "session_id": session_id})
    except Exception as e:
        print(f"Current chat error: {e}")
        return jsonify({"messages": [], "session_id": get_current_session(request.current_user['user_id'])})

@app.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations():
    try:
        limit = int(request.args.get('limit', 10))
        skip = int(request.args.get('skip', 0))
        
        conversations = list(db.conversations.find(
            {'user_id': request.current_user['user_id']},
            {'_id': 0, 'user_message': 1, 'bot_response': 1, 'timestamp': 1, 'conversation_id': 1}
        ).sort('timestamp', -1).skip(skip).limit(limit)) if db is not None else []
        
        return jsonify({"conversations": conversations})
    except Exception as e:
        print(f"Conversations error: {e}")
        return jsonify({"conversations": []})

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile():
    try:
        user_data = db.users.find_one(
            {"user_id": request.current_user['user_id']},
            {'_id': 0, 'password': 0}
        ) if db is not None else None
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({"user": user_data})
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "mongodb": "connected" if db is not None else "disconnected",
            "health_bot": "available",
            "kafka": "connected" if KAFKA_ENABLED else "disabled"
        },
        "version": "3.0.0"
    }
    return jsonify(status)

@app.route('/api/debug/status', methods=['GET'])
@token_required
def debug_status():
    """Debug endpoint to check API status"""
    user_id = request.current_user['user_id']
    
    status = {
        "user_id": user_id,
        "database_connected": db is not None,
        "health_bot_available": True,
        "kafka_enabled": KAFKA_ENABLED,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Test database operations
    if db is not None:
        try:
            # Test user query
            user = db.users.find_one({"user_id": user_id})
            status["user_exists"] = user is not None
            
            # Test conversations count
            conv_count = db.conversations.count_documents({"user_id": user_id})
            status["conversation_count"] = conv_count
            
            # Test sessions count
            session_count = db.chat_sessions.count_documents({"user_id": user_id})
            status["session_count"] = session_count
            
        except Exception as e:
            status["database_error"] = str(e)
    
    return jsonify(status)

# HTML Templates (YOUR EXISTING FRONTEND - KEEP EXACTLY THE SAME)
HTML_TEMPLATES = {
    'index': '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>HealthBot - Your AI Health Assistant</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @keyframes float {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .float-animation { animation: float 3s ease-in-out infinite; }
            .fade-in { animation: fadeIn 0.6s ease-out; }
            .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen">
        <!-- Animated Background -->
        <div class="fixed inset-0 gradient-bg opacity-10 z-0"></div>
        
        <nav class="bg-white/80 backdrop-blur-lg shadow-lg relative z-10">
            <div class="container mx-auto px-6 py-4 flex justify-between items-center">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 health-gradient rounded-full flex items-center justify-center float-animation">
                        <i class="fas fa-heartbeat text-white"></i>
                    </div>
                    <h1 class="text-2xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                        HealthBot
                    </h1>
                </div>
                <div id="auth-buttons" class="flex space-x-3">
                    <a href="/login" class="bg-white text-green-600 px-6 py-2 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 border border-green-200">
                        <i class="fas fa-sign-in-alt mr-2"></i>Login
                    </a>
                    <a href="/register" class="health-gradient text-white px-6 py-2 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105">
                        <i class="fas fa-user-plus mr-2"></i>Register
                    </a>
                </div>
            </div>
        </nav>

        <!-- Hero Section -->
        <div class="relative z-10 container mx-auto px-6 py-20 text-center fade-in">
            <div class="max-w-4xl mx-auto">
                <div class="w-24 h-24 mx-auto mb-8 health-gradient rounded-full flex items-center justify-center float-animation">
                    <i class="fas fa-heartbeat text-white text-3xl"></i>
                </div>
                <h2 class="text-5xl font-bold mb-6 bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                    Your AI Health Assistant
                </h2>
                <p class="text-xl text-gray-600 mb-8 leading-relaxed">
                    Get personalized health advice, symptom checking, and wellness guidance 
                    powered by advanced AI technology.
                </p>
                <div class="flex justify-center space-x-6">
                    <a href="/chat" class="group health-gradient text-white px-8 py-4 rounded-full text-lg font-semibold shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-110">
                        <i class="fas fa-comments mr-3 group-hover:scale-110 transition-transform"></i>
                        Start Chatting
                    </a>
                    <a href="#features" class="group border-2 border-green-500 text-green-600 px-8 py-4 rounded-full text-lg font-semibold hover:bg-green-500 hover:text-white transition-all duration-300">
                        <i class="fas fa-star mr-3"></i>
                        Learn More
                    </a>
                </div>
            </div>
        </div>

        <!-- Features Section -->
        <div id="features" class="relative z-10 container mx-auto px-6 py-16">
            <div class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                <div class="bg-white/80 backdrop-blur-lg p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 hover:transform hover:scale-105 border border-gray-100">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                        <i class="fas fa-brain text-green-600 text-2xl"></i>
                    </div>
                    <h3 class="text-xl font-bold text-center mb-4">AI Health Analysis</h3>
                    <p class="text-gray-600 text-center">Advanced AI algorithms for personalized health insights</p>
                </div>
                <div class="bg-white/80 backdrop-blur-lg p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 hover:transform hover:scale-105 border border-gray-100">
                    <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                        <i class="fas fa-bolt text-blue-600 text-2xl"></i>
                    </div>
                    <h3 class="text-xl font-bold text-center mb-4">24/7 Support</h3>
                    <p class="text-gray-600 text-center">Instant health guidance anytime you need it</p>
                </div>
                <div class="bg-white/80 backdrop-blur-lg p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 hover:transform hover:scale-105 border border-gray-100">
                    <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-6 mx-auto">
                        <i class="fas fa-shield-alt text-purple-600 text-2xl"></i>
                    </div>
                    <h3 class="text-xl font-bold text-center mb-4">Privacy First</h3>
                    <p class="text-gray-600 text-center">Your health data is always secure and private</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''',

    'login': '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - HealthBot</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .fade-in-up { animation: fadeInUp 0.6s ease-out; }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
        </style>
    </head>
    <body class="min-h-screen health-gradient">
        <div class="min-h-screen flex items-center justify-center p-4">
            <div class="bg-white/10 backdrop-blur-lg p-8 rounded-2xl shadow-2xl w-full max-w-md border border-white/20 fade-in-up">
                <div class="text-center mb-8">
                    <div class="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-heartbeat text-white text-3xl"></i>
                    </div>
                    <h2 class="text-3xl font-bold text-white">Welcome Back</h2>
                    <p class="text-white/80 mt-2">Sign in to HealthBot</p>
                </div>
                
                <form id="loginForm" class="space-y-6">
                    <div>
                        <label class="block text-white text-sm font-medium mb-2">Email</label>
                        <div class="relative">
                            <i class="fas fa-envelope absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60"></i>
                            <input type="email" name="email" class="w-full bg-white/20 text-white placeholder-white/60 border border-white/30 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all duration-300" placeholder="Enter your email" required>
                        </div>
                    </div>
                    
                    <div>
                        <label class="block text-white text-sm font-medium mb-2">Password</label>
                        <div class="relative">
                            <i class="fas fa-lock absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60"></i>
                            <input type="password" name="password" class="w-full bg-white/20 text-white placeholder-white/60 border border-white/30 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all duration-300" placeholder="Enter your password" required>
                        </div>
                    </div>
                    
                    <button type="submit" class="w-full bg-white text-green-600 font-semibold py-3 rounded-lg hover:bg-gray-100 transform hover:scale-105 transition-all duration-300 shadow-lg">
                        <i class="fas fa-sign-in-alt mr-2"></i>Sign In
                    </button>
                </form>
                
                <p class="text-white text-center mt-6">
                    Don't have an account? 
                    <a href="/register" class="text-white font-semibold hover:underline ml-1">Create one here</a>
                </p>
                
                <div id="message" class="mt-4"></div>
            </div>
        </div>

        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const button = e.target.querySelector('button[type="submit"]');
                const originalText = button.innerHTML;
                
                button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Signing In...';
                button.disabled = true;
                
                const formData = new FormData(e.target);
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(Object.fromEntries(formData))
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        localStorage.setItem('token', data.token);
                        localStorage.setItem('user_name', data.name);
                        // Show success animation
                        button.innerHTML = '<i class="fas fa-check mr-2"></i>Success!';
                        button.classList.remove('bg-white', 'text-green-600');
                        button.classList.add('bg-green-500', 'text-white');
                        setTimeout(() => {
                            window.location.href = '/chat';
                        }, 1000);
                    } else {
                        document.getElementById('message').innerHTML = 
                            `<div class="bg-red-500/80 text-white p-3 rounded-lg text-center fade-in-up">
                                <i class="fas fa-exclamation-triangle mr-2"></i>${data.error}
                            </div>`;
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }
                } catch (error) {
                    document.getElementById('message').innerHTML = 
                        `<div class="bg-red-500/80 text-white p-3 rounded-lg text-center fade-in-up">
                            <i class="fas fa-exclamation-triangle mr-2"></i>Network error
                        </div>`;
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    ''',

    'register': '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Register - HealthBot</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .fade-in-up { animation: fadeInUp 0.6s ease-out; }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
        </style>
    </head>
    <body class="min-h-screen health-gradient">
        <div class="min-h-screen flex items-center justify-center p-4">
            <div class="bg-white/10 backdrop-blur-lg p-8 rounded-2xl shadow-2xl w-full max-w-md border border-white/20 fade-in-up">
                <div class="text-center mb-8">
                    <div class="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-user-plus text-white text-3xl"></i>
                    </div>
                    <h2 class="text-3xl font-bold text-white">Join HealthBot</h2>
                    <p class="text-white/80 mt-2">Create your health assistant account</p>
                </div>
                
                <form id="registerForm" class="space-y-6">
                    <div>
                        <label class="block text-white text-sm font-medium mb-2">Full Name</label>
                        <div class="relative">
                            <i class="fas fa-user absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60"></i>
                            <input type="text" name="name" class="w-full bg-white/20 text-white placeholder-white/60 border border-white/30 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all duration-300" placeholder="Enter your full name" required>
                        </div>
                    </div>
                    
                    <div>
                        <label class="block text-white text-sm font-medium mb-2">Email</label>
                        <div class="relative">
                            <i class="fas fa-envelope absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60"></i>
                            <input type="email" name="email" class="w-full bg-white/20 text-white placeholder-white/60 border border-white/30 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all duration-300" placeholder="Enter your email" required>
                        </div>
                    </div>
                    
                    <div>
                        <label class="block text-white text-sm font-medium mb-2">Password</label>
                        <div class="relative">
                            <i class="fas fa-lock absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60"></i>
                            <input type="password" name="password" class="w-full bg-white/20 text-white placeholder-white/60 border border-white/30 rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent transition-all duration-300" placeholder="Create a password" required>
                        </div>
                    </div>
                    
                    <button type="submit" class="w-full health-gradient text-white font-semibold py-3 rounded-lg hover:opacity-90 transform hover:scale-105 transition-all duration-300 shadow-lg">
                        <i class="fas fa-user-plus mr-2"></i>Create Account
                    </button>
                </form>
                
                <p class="text-white text-center mt-6">
                    Already have an account? 
                    <a href="/login" class="text-white font-semibold hover:underline ml-1">Sign in here</a>
                </p>
                
                <div id="message" class="mt-4"></div>
            </div>
        </div>

        <script>
            document.getElementById('registerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const button = e.target.querySelector('button[type="submit"]');
                const originalText = button.innerHTML;
                
                button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating Account...';
                button.disabled = true;
                
                const formData = new FormData(e.target);
                try {
                    const response = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(Object.fromEntries(formData))
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        localStorage.setItem('token', data.token);
                        // Show success animation
                        button.innerHTML = '<i class="fas fa-check mr-2"></i>Account Created!';
                        button.classList.add('bg-green-500', 'text-white');
                        setTimeout(() => {
                            window.location.href = '/chat';
                        }, 1000);
                    } else {
                        document.getElementById('message').innerHTML = 
                            `<div class="bg-red-500/80 text-white p-3 rounded-lg text-center fade-in-up">
                                <i class="fas fa-exclamation-triangle mr-2"></i>${data.error}
                            </div>`;
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }
                } catch (error) {
                    document.getElementById('message').innerHTML = 
                        `<div class="bg-red-500/80 text-white p-3 rounded-lg text-center fade-in-up">
                            <i class="fas fa-exclamation-triangle mr-2"></i>Network error
                        </div>`;
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    ''',

    'chat': '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat - HealthBot</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @keyframes slideInUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes bounceIn {
                0% { transform: scale(0.3); opacity: 0; }
                50% { transform: scale(1.05); }
                70% { transform: scale(0.9); }
                100% { transform: scale(1); opacity: 1; }
            }
            .slide-in-up { animation: slideInUp 0.3s ease-out; }
            .bounce-in { animation: bounceIn 0.6s ease-out; }
            .chat-bubble-user { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-bottom-right-radius: 4px;
            }
            .chat-bubble-bot { 
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                border-bottom-left-radius: 4px;
            }
            .typing-indicator {
                display: inline-flex;
                align-items: center;
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                padding: 12px 16px;
                border-radius: 18px;
                border-bottom-left-radius: 4px;
            }
            .typing-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: rgba(255, 255, 255, 0.7);
                margin: 0 2px;
                animation: typing 1.4s infinite ease-in-out;
            }
            .typing-dot:nth-child(1) { animation-delay: -0.32s; }
            .typing-dot:nth-child(2) { animation-delay: -0.16s; }
            @keyframes typing {
                0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
                40% { transform: scale(1); opacity: 1; }
            }
            .message-enter {
                animation: slideInUp 0.3s ease-out;
            }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
            .glass-effect { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
            .disclaimer {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                color: white;
                padding: 12px 16px;
                border-radius: 12px;
                margin: 10px 0;
                font-size: 0.9em;
                border-left: 4px solid #ff3838;
            }
            .chat-history-item {
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .chat-history-item:hover {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                transform: translateX(5px);
            }
            .active-chat {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
            }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen">
        <!-- Animated Background -->
        <div class="fixed inset-0 health-gradient opacity-10 z-0"></div>
        
        <nav class="bg-white/80 backdrop-blur-lg shadow-lg relative z-10">
            <div class="container mx-auto px-6 py-4 flex justify-between items-center">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 health-gradient rounded-full flex items-center justify-center">
                        <i class="fas fa-heartbeat text-white"></i>
                    </div>
                    <h1 class="text-2xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                        HealthBot
                    </h1>
                </div>
                <div class="flex items-center space-x-4">
                    <span id="user-info" class="text-gray-700 font-medium">
                        <i class="fas fa-user mr-2"></i>Welcome!
                    </span>
                    <a href="/profile" class="text-green-600 hover:text-green-800 transition-colors">
                        <i class="fas fa-user-cog mr-1"></i>Profile
                    </a>
                    <button onclick="logout()" class="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors">
                        <i class="fas fa-sign-out-alt mr-2"></i>Logout
                    </button>
                </div>
            </div>
        </nav>

        <!-- Main Chat Container -->
        <div class="container mx-auto px-4 py-8 max-w-6xl relative z-10">
            <div class="flex gap-6">
                <!-- Chat History Sidebar -->
                <div class="w-80 bg-white rounded-2xl shadow-2xl overflow-hidden glass-effect border border-white/20 h-[600px]">
                    <div class="health-gradient p-4 text-white">
                        <div class="flex justify-between items-center">
                            <h3 class="text-lg font-bold">Chat History</h3>
                            <button onclick="startNewChat()" class="bg-white text-green-600 px-3 py-1 rounded-lg text-sm hover:bg-gray-100 transition-colors">
                                <i class="fas fa-plus mr-1"></i>New
                            </button>
                        </div>
                    </div>
                    <div class="p-4 h-[520px] overflow-y-auto">
                        <div id="chat-history" class="space-y-2">
                            <!-- Chat history will be loaded here -->
                        </div>
                    </div>
                </div>

                <!-- Chat Container -->
                <div class="flex-1 bg-white rounded-2xl shadow-2xl overflow-hidden glass-effect border border-white/20">
                    <!-- Chat Header -->
                    <div class="health-gradient p-6 text-white">
                        <div class="flex items-center space-x-4">
                            <div class="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                                <i class="fas fa-heartbeat text-2xl"></i>
                            </div>
                            <div>
                                <h2 class="text-2xl font-bold">Health Assistant</h2>
                                <p class="text-green-100">Ready to help with your health questions!</p>
                            </div>
                        </div>
                        <!-- Medical Disclaimer -->
                        <div class="disclaimer mt-4 text-sm">
                            <i class="fas fa-exclamation-triangle mr-2"></i>
                            <strong>Important:</strong> I am an AI assistant. For medical concerns, always consult a healthcare professional.
                        </div>
                    </div>

                    <!-- Chat Messages -->
                    <div id="chat-messages" class="h-96 overflow-y-auto p-6 bg-gray-50/50">
                        <div class="text-center text-gray-500 py-8">
                            <i class="fas fa-comments text-4xl mb-4 opacity-50"></i>
                            <p class="text-lg">Start a conversation with your health assistant</p>
                            <p class="text-sm text-gray-400 mt-2">Ask about symptoms, health advice, or general wellness</p>
                        </div>
                    </div>

                    <!-- Quick Actions -->
                    <div class="p-4 bg-gray-100 border-t border-gray-200">
                        <div class="flex flex-wrap justify-center gap-2">
                            <button onclick="addQuickMessage('What are common cold symptoms?')" 
                                    class="bg-white text-gray-700 px-4 py-2 rounded-full text-sm hover:bg-green-50 hover:text-green-600 transition-all duration-300 border border-gray-200 hover:border-green-300 shadow-sm">
                                🤒 Cold Symptoms
                            </button>
                            <button onclick="addQuickMessage('How to improve sleep quality?')" 
                                    class="bg-white text-gray-700 px-4 py-2 rounded-full text-sm hover:bg-blue-50 hover:text-blue-600 transition-all duration-300 border border-gray-200 hover:border-blue-300 shadow-sm">
                                😴 Sleep Tips
                            </button>
                            <button onclick="addQuickMessage('Healthy diet recommendations')" 
                                    class="bg-white text-gray-700 px-4 py-2 rounded-full text-sm hover:bg-yellow-50 hover:text-yellow-600 transition-all duration-300 border border-gray-200 hover:border-yellow-300 shadow-sm">
                                🥗 Diet Advice
                            </button>
                            <button onclick="addQuickMessage('Exercise and fitness tips')" 
                                    class="bg-white text-gray-700 px-4 py-2 rounded-full text-sm hover:bg-purple-50 hover:text-purple-600 transition-all duration-300 border border-gray-200 hover:border-purple-300 shadow-sm">
                                💪 Fitness Tips
                            </button>
                        </div>
                    </div>

                    <!-- Chat Input -->
                    <div class="p-6 bg-white border-t border-gray-200">
                        <div class="flex space-x-4">
                            <input type="text" id="message-input" 
                                   class="flex-1 p-4 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all duration-300 shadow-lg"
                                   placeholder="Ask about symptoms, health advice, or general wellness..." 
                                   onkeypress="handleKeyPress(event)">
                            <button onclick="sendMessage()" id="send-button"
                                    class="health-gradient text-white px-8 py-4 rounded-2xl hover:opacity-90 transform hover:scale-105 transition-all duration-300 shadow-lg font-semibold">
                                <i class="fas fa-paper-plane mr-2"></i>Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login';
            }

            // Display user info
            const userName = localStorage.getItem('user_name') || 'User';
            document.getElementById('user-info').innerHTML = `<i class="fas fa-user mr-2"></i>${userName}`;

            let isTyping = false;
            let currentSessionId = null;
            let chatHistory = [];

            // Load chat history on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadChatHistory();
                loadCurrentChat();
            });

            async function loadChatHistory() {
                try {
                    const response = await fetch('/api/chat/history?days=30', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        chatHistory = data.sessions || [];
                        displayChatHistory();
                    } else {
                        console.error('Failed to load chat history:', data.error);
                        document.getElementById('chat-history').innerHTML = 
                            '<div class="text-gray-500 text-center py-4">Failed to load chat history</div>';
                    }
                } catch (error) {
                    console.error('Error loading chat history:', error);
                    document.getElementById('chat-history').innerHTML = 
                        '<div class="text-gray-500 text-center py-4">Error loading chat history</div>';
                }
            }

            function displayChatHistory() {
                const historyContainer = document.getElementById('chat-history');
                historyContainer.innerHTML = '';

                if (chatHistory.length === 0) {
                    historyContainer.innerHTML = '<div class="text-gray-500 text-center py-4">No chat history yet</div>';
                    return;
                }

                // Group sessions by date
                const sessionsByDate = {};
                chatHistory.forEach(session => {
                    const date = new Date(session.date).toLocaleDateString();
                    if (!sessionsByDate[date]) {
                        sessionsByDate[date] = [];
                    }
                    sessionsByDate[date].push(session);
                });

                // Display sessions grouped by date
                Object.keys(sessionsByDate).forEach(date => {
                    const dateHeader = document.createElement('div');
                    dateHeader.className = 'text-sm font-semibold text-gray-500 mb-2 mt-4 first:mt-0';
                    dateHeader.textContent = date;
                    historyContainer.appendChild(dateHeader);

                    sessionsByDate[date].forEach(session => {
                        const sessionElement = document.createElement('div');
                        sessionElement.className = `chat-history-item p-3 rounded-lg border border-gray-200 ${
                            session.session_id === currentSessionId ? 'active-chat' : 'bg-gray-50'
                        }`;
                        sessionElement.innerHTML = `
                            <div class="flex justify-between items-start">
                                <div class="flex-1">
                                    <div class="font-medium text-sm">${session.preview || 'New conversation'}</div>
                                    <div class="text-xs text-gray-500 mt-1">${session.message_count || 0} messages</div>
                                </div>
                                <div class="text-xs text-gray-400">${new Date(session.date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                            </div>
                        `;
                        sessionElement.onclick = () => loadChatSession(session.session_id);
                        historyContainer.appendChild(sessionElement);
                    });
                });
            }

            async function loadChatSession(sessionId) {
                try {
                    const response = await fetch(`/api/chat/session/${sessionId}`, {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    const data = await response.json();
                    
                    if (response.ok) {
                        currentSessionId = sessionId;
                        displayChatMessages(data.messages || []);
                        displayChatHistory(); // Update active chat highlight
                    } else {
                        console.error('Failed to load chat session:', data.error);
                    }
                } catch (error) {
                    console.error('Error loading chat session:', error);
                }
            }

            async function loadCurrentChat() {
                try {
                    const response = await fetch('/api/chat/current', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    const data = await response.json();
                    
                    if (response.ok && data.session_id) {
                        currentSessionId = data.session_id;
                        if (data.messages && data.messages.length > 0) {
                            displayChatMessages(data.messages);
                        }
                        displayChatHistory(); // Update active chat highlight
                    }
                } catch (error) {
                    console.error('Error loading current chat:', error);
                }
            }

            function displayChatMessages(messages) {
                const chatContainer = document.getElementById('chat-messages');
                chatContainer.innerHTML = '';

                if (messages.length === 0) {
                    chatContainer.innerHTML = `
                        <div class="text-center text-gray-500 py-8">
                            <i class="fas fa-comments text-4xl mb-4 opacity-50"></i>
                            <p class="text-lg">Start a conversation with your health assistant</p>
                        </div>
                    `;
                    return;
                }

                messages.forEach(message => {
                    addMessageToDisplay(message.sender, message.text, message.timestamp, false);
                });
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            function startNewChat() {
                currentSessionId = null;
                document.getElementById('chat-messages').innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <i class="fas fa-comments text-4xl mb-4 opacity-50"></i>
                        <p class="text-lg">Start a new conversation with your health assistant</p>
                    </div>
                `;
                document.getElementById('message-input').value = '';
                displayChatHistory(); // Update active chat highlight
            }

            function handleKeyPress(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            }

            function addQuickMessage(message) {
                document.getElementById('message-input').value = message;
                sendMessage();
            }

            async function sendMessage() {
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                if (!message || isTyping) return;

                // Add user message
                addMessageToDisplay('user', message, new Date().toISOString(), true);
                input.value = '';
                
                // Show typing indicator
                showTypingIndicator();
                isTyping = true;

                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({
                            message: message,
                            session_id: currentSessionId
                        })
                    });
                    
                    const data = await response.json();
                    hideTypingIndicator();
                    isTyping = false;
                    
                    if (response.ok) {
                        currentSessionId = data.session_id;
                        addMessageToDisplay('bot', data.response, new Date().toISOString(), true);
                        
                        // Reload chat history to show updated session
                        loadChatHistory();
                    } else {
                        addMessageToDisplay('bot', 'Sorry, I encountered an error. Please try again.', new Date().toISOString(), true);
                    }
                } catch (error) {
                    hideTypingIndicator();
                    isTyping = false;
                    addMessageToDisplay('bot', 'Network error. Please check your connection.', new Date().toISOString(), true);
                }
            }

            function addMessageToDisplay(sender, text, timestamp, animate = true) {
                const chat = document.getElementById('chat-messages');
                
                // Remove welcome message if it's the first real message
                if (chat.children.length === 1 && chat.children[0].classList.contains('text-center')) {
                    chat.innerHTML = '';
                }

                const messageDiv = document.createElement('div');
                messageDiv.className = `mb-4 ${animate ? 'message-enter' : ''} ${sender === 'user' ? 'text-right' : 'text-left'}`;
                
                const time = new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                messageDiv.innerHTML = `
                    <div class="inline-block max-w-xs lg:max-w-md px-4 py-3 rounded-2xl text-white shadow-lg ${
                        sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-bot'
                    }">
                        ${text}
                    </div>
                    <div class="text-xs text-gray-500 mt-1 ${sender === 'user' ? 'text-right' : 'text-left'}">
                        ${time}
                    </div>
                `;
                
                chat.appendChild(messageDiv);
                chat.scrollTop = chat.scrollHeight;
            }

            function showTypingIndicator() {
                const chat = document.getElementById('chat-messages');
                const typingDiv = document.createElement('div');
                typingDiv.id = 'typing-indicator';
                typingDiv.className = 'mb-4 message-enter';
                typingDiv.innerHTML = `
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                `;
                chat.appendChild(typingDiv);
                chat.scrollTop = chat.scrollHeight;
            }

            function hideTypingIndicator() {
                const typingIndicator = document.getElementById('typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }

            function logout() {
                localStorage.clear();
                window.location.href = '/';
            }
        </script>
    </body>
    </html>
    ''',

    'profile': '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Profile - HealthBot</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .fade-in { animation: fadeIn 0.6s ease-out; }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
            .glass-effect { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); }
        </style>
    </head>
    <body class="min-h-screen health-gradient">
        <nav class="bg-white/80 backdrop-blur-lg shadow-lg">
            <div class="container mx-auto px-6 py-4 flex justify-between items-center">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 health-gradient rounded-full flex items-center justify-center">
                        <i class="fas fa-heartbeat text-white"></i>
                    </div>
                    <h1 class="text-2xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                        HealthBot
                    </h1>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/chat" class="text-green-600 hover:text-green-800 transition-colors">
                        <i class="fas fa-comments mr-1"></i>Chat
                    </a>
                    <button onclick="logout()" class="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors">
                        <i class="fas fa-sign-out-alt mr-2"></i>Logout
                    </button>
                </div>
            </div>
        </nav>

        <div class="container mx-auto px-4 py-8 max-w-2xl">
            <div class="glass-effect rounded-2xl shadow-2xl p-8 border border-white/20 fade-in">
                <div class="text-center mb-8">
                    <div class="w-24 h-24 health-gradient rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-user text-white text-3xl"></i>
                    </div>
                    <h2 class="text-3xl font-bold text-white">User Profile</h2>
                    <p class="text-white/80 mt-2">Manage your health assistant account</p>
                </div>

                <div id="profile-data" class="space-y-6">
                    <div class="bg-white/10 rounded-xl p-6 border border-white/20">
                        <div class="flex justify-between items-center border-b border-white/20 pb-4 mb-4">
                            <span class="font-semibold text-white text-lg">Name:</span>
                            <span id="user-name" class="text-white/90 text-lg">Loading...</span>
                        </div>
                        <div class="flex justify-between items-center border-b border-white/20 pb-4 mb-4">
                            <span class="font-semibold text-white text-lg">Email:</span>
                            <span id="user-email" class="text-white/90 text-lg">Loading...</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="font-semibold text-white text-lg">Member Since:</span>
                            <span id="user-created" class="text-white/90 text-lg">Loading...</span>
                        </div>
                    </div>

                    <div class="bg-white/10 rounded-xl p-6 border border-white/20">
                        <h3 class="text-xl font-bold text-white mb-4">Health Statistics</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="text-center">
                                <div class="text-2xl font-bold text-white" id="conversation-count">0</div>
                                <div class="text-white/70 text-sm">Health Conversations</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-white" id="messages-count">0</div>
                                <div class="text-white/70 text-sm">Total Messages</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const token = localStorage.getItem('token');
            if (!token) window.location.href = '/login';
            
            async function loadProfile() {
                try {
                    const response = await fetch('/api/user/profile', {
                        headers: {'Authorization': 'Bearer ' + token}
                    });
                    const data = await response.json();
                    if (response.ok) {
                        document.getElementById('user-name').textContent = data.user.name;
                        document.getElementById('user-email').textContent = data.user.email;
                        document.getElementById('user-created').textContent = new Date(data.user.created_at).toLocaleDateString();
                        
                        // Load conversation stats
                        const convResponse = await fetch('/api/conversations?limit=100', {
                            headers: {'Authorization': 'Bearer ' + token}
                        });
                        const convData = await convResponse.json();
                        if (convResponse.ok) {
                            document.getElementById('conversation-count').textContent = convData.conversations.length;
                            const totalMessages = convData.conversations.reduce((acc, conv) => acc + 2, 0);
                            document.getElementById('messages-count').textContent = totalMessages;
                        }
                    }
                } catch (error) {
                    console.error('Error loading profile:', error);
                }
            }
            
            function logout() {
                localStorage.clear();
                window.location.href = '/';
            }
            
            loadProfile();
        </script>
    </body>
    </html>
    '''
}

if __name__ == '__main__':
    print("🚀 Starting HealthBot - AI Health Assistant...")
    print("📊 MongoDB:", "Connected" if db is not None else "Disconnected")
    print("🤖 Health Bot:", "✅ Available with smart responses")
    print("📨 Kafka:", "Enabled" if KAFKA_ENABLED else "Disabled")
    print("🌐 Live at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)