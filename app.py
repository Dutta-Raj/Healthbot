import os
import time
import json
import jwt
import bcrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, Response
from functools import wraps
from pymongo import MongoClient, errors
from bson import ObjectId
import google.generativeai as genai
import certifi

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# --- Configuration ---
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBfq-N5ML_HDJwVuuGuUXCvS-gVp4esJr0")
JWT_SECRET = os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production")

MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"

# --- Database & AI Initialization ---
chats_collection = None
users_collection = None
model = None

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

# Gemini AI Setup
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("✅ Gemini initialized successfully.")
except Exception as e:
    print(f"❌ Gemini initialization failed: {e}")
    model = None

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

        # Check if user already exists - FIXED: Proper None check
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

        # FIXED: Proper collection check
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

        # Find user - FIXED: Proper None check
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
    ai_status = "connected" if model is not None else "disconnected"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "ai_service": ai_status,
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

# --- Your Existing Home Route (Keep your original HTML template) ---
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
          max-width: 1200px;
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
      }

      /* Chat Interface Styles */
      .chat-container {
          width: 100%;
          height: 100%;
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
        
        <!-- Chat App Container -->
        <div id="chatAppContainer"></div>
      </div>

      <script>
        let authToken = null;
        let currentUserId = null;
        let currentUserName = null;

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
          
          // Load the chat application
          loadChatApp();
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
                        Hello ${currentUserName}! I'm HealthQ, your AI health assistant. How can I help you today? 😊
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
                        session_id: window.currentSessionId || null
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'message bot-message';
                chatMessages.appendChild(botMessageDiv);
                
                // Hide typing indicator
                typingIndicator.style.display = 'none';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    
                    // Check if it's a session ID script
                    if (chunk.includes('currentSessionId')) {
                        const match = chunk.match(/currentSessionId = '([^']+)'/);
                        if (match) {
                            window.currentSessionId = match[1];
                        }
                        continue;
                    }
                    
                    // Append to bot message
                    botMessageDiv.textContent += chunk;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
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

# --- Your Existing Chat Routes (Updated with Authentication) ---
@app.route("/chat", methods=["POST"])
@token_required
def chat(current_user):
    user_msg = request.json.get("message")
    session_id = request.json.get("session_id")

    if not model:
        return jsonify({"error": "Gemini AI is not available"}), 500

    def generate():
        try:
            response_text = ""
            response = model.generate_content(user_msg, stream=True)

            for chunk in response:
                if chunk.text:
                    response_text += chunk.text
                    yield chunk.text

            disclaimer = "\n\n⚠️ Note: I am not a doctor. Please consult a healthcare professional for serious concerns."
            response_text += disclaimer
            yield disclaimer

            # Save to database if available - NOW WITH USER ID
            if chats_collection is not None:
                try:
                    chat_data = {
                        "user_id": current_user,
                        "user": user_msg,
                        "bot": response_text,
                        "timestamp": datetime.now()
                    }
                    
                    if session_id:
                        chats_collection.update_one(
                            {"_id": ObjectId(session_id), "user_id": current_user},
                            {"$set": chat_data}
                        )
                    else:
                        result = chats_collection.insert_one(chat_data)
                        yield f"<script>currentSessionId = '{result.inserted_id}';</script>"
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    yield ""

        except Exception as e:
            yield f"⚠️ Error: {str(e)}"

    return Response(generate(), mimetype="text/plain")

@app.route("/history", methods=["GET"])
@token_required
def history(current_user):
    try:
        if chats_collection is not None:
            # NEW: Only get chats for this user
            chats = list(chats_collection.find(
                {"user_id": current_user}
            ).sort("timestamp", -1).limit(10))
            return jsonify(chats)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify([])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
