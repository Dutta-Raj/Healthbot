import os
import jwt
import uuid
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
from dotenv import load_dotenv
import cohere
from bcrypt import hashpw, gensalt, checkpw
from kafka import KafkaProducer, KafkaConsumer

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-2024')

# Medical Disclaimer
MEDICAL_DISCLAIMER = """**Important Medical Disclaimer**: 
I am an AI assistant and not a medical professional. My advice is for informational purposes only and should not be considered medical advice. Always consult with a qualified healthcare provider for medical concerns, diagnoses, or treatment. In case of emergency, contact emergency services immediately."""

HEALTH_PROMPT_TEMPLATE = """As a health assistant, provide helpful, accurate, and safe health information. Follow these guidelines:

1. Be empathetic and supportive
2. Provide general wellness information
3. For specific symptoms or medical conditions, recommend consulting a healthcare professional
4. Never diagnose conditions or prescribe treatments
5. Always include a disclaimer about consulting doctors
6. Be clear that you're an AI assistant
7. Focus on prevention and general wellness

Current conversation:
User: {user_message}
Health Assistant:"""

# MongoDB Configuration
try:
    mongo_uri = f"mongodb+srv://{os.getenv('MONGO_USERNAME')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_CLUSTER')}/{os.getenv('MONGO_DB_NAME')}?retryWrites=true&w=majority"
    client = MongoClient(mongo_uri)
    db = client[os.getenv('MONGO_DB_NAME')]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    client, db = None, None

# Cohere AI Configuration
try:
    cohere_client = cohere.Client(os.getenv('COHERE_API_KEY'))
    print("✅ Cohere AI configured successfully!")
except Exception as e:
    print(f"❌ Cohere AI configuration failed: {e}")
    cohere_client = None

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
        if db:
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
    if not db:
        return str(uuid.uuid4())
    
    # Get today's session or create new one
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    session = db.chat_sessions.find_one({
        "user_id": user_id,
        "created_at": {"$gte": today_start}
    })
    
    if not session:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "message_count": 0
        }
        db.chat_sessions.insert_one(session_data)
        return session_id
    
    return session["session_id"]

# Animated Frontend Templates
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
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .float-animation { animation: float 3s ease-in-out infinite; }
            .fade-in { animation: fadeIn 0.6s ease-out; }
            .pulse-animation { animation: pulse 2s ease-in-out infinite; }
            .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .health-gradient { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }
            .chat-bubble-user { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-bottom-right-radius: 4px;
            }
            .chat-bubble-bot { 
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                border-bottom-left-radius: 4px;
            }
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
                            <button onclick="toggleVoice()" id="voice-button"
                                    class="bg-blue-500 text-white px-4 py-4 rounded-2xl hover:bg-blue-600 transform hover:scale-105 transition-all duration-300 shadow-lg">
                                <i class="fas fa-microphone"></i>
                            </button>
                            <button onclick="stopResponse()" id="stop-button" style="display: none;"
                                    class="bg-red-500 text-white px-4 py-4 rounded-2xl hover:bg-red-600 transform hover:scale-105 transition-all duration-300 shadow-lg">
                                <i class="fas fa-stop"></i>
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
            let currentSpeech = null;
            let isVoiceEnabled = false;
            let stopResponseRequested = false;
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
                        chatHistory = data.sessions;
                        displayChatHistory();
                    }
                } catch (error) {
                    console.error('Error loading chat history:', error);
                }
            }

            function displayChatHistory() {
                const historyContainer = document.getElementById('chat-history');
                historyContainer.innerHTML = '';

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
                                    <div class="text-xs text-gray-500 mt-1">${session.message_count} messages</div>
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
                        displayChatMessages(data.messages);
                        displayChatHistory(); // Update active chat highlight
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

            function toggleVoice() {
                isVoiceEnabled = !isVoiceEnabled;
                const voiceButton = document.getElementById('voice-button');
                if (isVoiceEnabled) {
                    voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                    voiceButton.classList.remove('bg-blue-500');
                    voiceButton.classList.add('bg-purple-500');
                    speakText('Voice mode activated');
                } else {
                    voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
                    voiceButton.classList.remove('bg-purple-500');
                    voiceButton.classList.add('bg-blue-500');
                    if (currentSpeech) {
                        currentSpeech.cancel();
                    }
                }
            }

            function stopResponse() {
                stopResponseRequested = true;
                if (currentSpeech) {
                    currentSpeech.cancel();
                }
                hideTypingIndicator();
                isTyping = false;
                document.getElementById('stop-button').style.display = 'none';
                document.getElementById('send-button').style.display = 'block';
            }

            function speakText(text) {
                if (!isVoiceEnabled) return;
                
                if ('speechSynthesis' in window) {
                    if (currentSpeech) {
                        currentSpeech.cancel();
                    }
                    
                    const speech = new SpeechSynthesisUtterance(text);
                    speech.rate = 0.8;
                    speech.pitch = 1;
                    speech.volume = 1;
                    
                    currentSpeech = speech;
                    window.speechSynthesis.speak(speech);
                    
                    speech.onend = function() {
                        currentSpeech = null;
                    };
                }
            }

            async function sendMessage() {
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                if (!message || isTyping) return;

                // Add user message
                addMessageToDisplay('user', message, new Date().toISOString(), true);
                input.value = '';
                
                // Show typing indicator and stop button
                showTypingIndicator();
                isTyping = true;
                stopResponseRequested = false;
                document.getElementById('stop-button').style.display = 'block';
                document.getElementById('send-button').style.display = 'none';

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
                    document.getElementById('stop-button').style.display = 'none';
                    document.getElementById('send-button').style.display = 'block';
                    
                    if (response.ok && !stopResponseRequested) {
                        currentSessionId = data.session_id;
                        addMessageToDisplay('bot', data.response, new Date().toISOString(), true);
                        
                        // Reload chat history to show updated session
                        loadChatHistory();
                        
                        // Speak the response if voice is enabled
                        if (isVoiceEnabled) {
                            speakText(data.response);
                        }
                    } else if (!response.ok) {
                        addMessageToDisplay('bot', 'Sorry, I encountered an error. Please try again.', new Date().toISOString(), true);
                    }
                } catch (error) {
                    hideTypingIndicator();
                    isTyping = false;
                    document.getElementById('stop-button').style.display = 'none';
                    document.getElementById('send-button').style.display = 'block';
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
                if (currentSpeech) {
                    currentSpeech.cancel();
                }
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
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
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

@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    if cohere_client is None:
        return jsonify({"error": "AI service unavailable"}), 503
        
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Get or create session
        if not session_id:
            session_id = get_current_session(request.current_user['user_id'])
        
        # Enhanced prompt with medical safety
        health_prompt = HEALTH_PROMPT_TEMPLATE.format(user_message=user_message)
        
        try:
            response = cohere_client.generate(
                model='command',
                prompt=health_prompt,
                max_tokens=200,
                temperature=0.7,
                stop_sequences=["\n\n"]
            )
            
            bot_response = response.generations[0].text.strip()
            
            # Add disclaimer for medical topics
            medical_keywords = ['symptom', 'pain', 'fever', 'headache', 'cough', 'cold', 'flu', 'disease', 'condition', 'diagnose', 'treatment', 'medicine', 'drug', 'pill']
            if any(keyword in user_message.lower() for keyword in medical_keywords):
                bot_response += f"\n\n{MEDICAL_DISCLAIMER}"
            
        except Exception as ai_error:
            print(f"Cohere API error: {ai_error}")
            bot_response = "I'm currently having trouble accessing health information. Please try again in a moment. For urgent medical concerns, please contact a healthcare provider directly."
        
        # Save conversation
        conversation_data = {
            'conversation_id': str(uuid.uuid4()),
            'session_id': session_id,
            'user_id': request.current_user['user_id'],
            'user_message': user_message,
            'bot_response': bot_response,
            'timestamp': datetime.utcnow()
        }
        
        if db:
            db.conversations.insert_one(conversation_data)
            
            # Update session message count
            db.chat_sessions.update_one(
                {"session_id": session_id},
                {"$inc": {"message_count": 1}},
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
        
        # Get unique sessions with their messages
        pipeline = [
            {"$match": {
                "user_id": request.current_user['user_id'],
                "timestamp": {"$gte": since_date}
            }},
            {"$group": {
                "_id": "$session_id",
                "last_message": {"$last": "$$ROOT"},
                "message_count": {"$sum": 1},
                "first_timestamp": {"$min": "$timestamp"}
            }},
            {"$sort": {"first_timestamp": -1}},
            {"$project": {
                "session_id": "$_id",
                "preview": {"$substr": ["$last_message.user_message", 0, 50]},
                "message_count": 1,
                "date": "$first_timestamp",
                "_id": 0
            }}
        ]
        
        sessions = list(db.conversations.aggregate(pipeline))
        
        return jsonify({"sessions": sessions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        ).sort('timestamp', 1))
        
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
        return jsonify({"error": str(e)}), 500

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
        ).sort('timestamp', 1))
        
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
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations():
    try:
        limit = int(request.args.get('limit', 10))
        skip = int(request.args.get('skip', 0))
        
        conversations = list(db.conversations.find(
            {'user_id': request.current_user['user_id']},
            {'_id': 0, 'user_message': 1, 'bot_response': 1, 'timestamp': 1, 'conversation_id': 1}
        ).sort('timestamp', -1).skip(skip).limit(limit))
        
        return jsonify({"conversations": conversations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile():
    try:
        user_data = db.users.find_one(
            {"user_id": request.current_user['user_id']},
            {'_id': 0, 'password': 0}
        )
        return jsonify({"user": user_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "mongodb": "connected" if db else "disconnected",
            "cohere_api": "available" if cohere_client else "unavailable",
            "kafka": "connected" if KAFKA_ENABLED else "disabled"
        },
        "version": "3.0.0"
    }
    return jsonify(status)

if __name__ == '__main__':
    print("🚀 Starting HealthBot - AI Health Assistant...")
    print("📊 MongoDB: Connected")
    print("🤖 Cohere AI: Available")
    print("📨 Kafka:", "Enabled" if KAFKA_ENABLED else "Disabled")
    print("🎤 Voice Features: Enabled")
    print("⏹️  Stop Button: Enabled")
    print("🔐 Authentication: JWT Enabled")
    print("💾 Database: MongoDB Atlas")
    print("📅 Chat History: 30 days retention")
    print("🆕 New Chat Sessions: Daily auto-creation")
    print("🌐 Live at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
