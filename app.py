import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, Response
from pymongo import MongoClient, errors
from bson import ObjectId
import google.generativeai as genai
import certifi

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
# Get credentials from .env file
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
GEMINI_API_KEY = "AIzaSyBfq-N5ML_HDJwVuuGuUXCvS-gVp4esJr0"

# Construct the MongoDB URI using environment variables
MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"


# --- Database & AI Initialization ---
chats_collection = None
model = None

# MongoDB Setup with retry logic
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        print(f"Attempting to connect to MongoDB... (Attempt {attempt + 1}/{max_retries})")
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsCAFile=certifi.where()
        )
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        db = client["healthq_db"]
        chats_collection = db["conversations"]
        print("✅ MongoDB connected successfully.")
        break
    except errors.ConnectionFailure as e:
        print(f"❌ ConnectionFailure: {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("❗ Failed to connect to MongoDB after multiple retries.")
            print("Using in-memory storage instead (data will not be saved).")
            chats_collection = None
    except errors.ConfigurationError as e:
        print(f"❌ ConfigurationError: {e}")
        print("Please check your network settings and the MongoDB Atlas connection string.")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("❗ Failed to connect to MongoDB due to a configuration error.")
            chats_collection = None
    except Exception as e:
        print(f"❌ An unexpected error occurred during MongoDB connection: {e}")
        chats_collection = None
        break

# Gemini AI Setup
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("✅ Gemini initialized successfully.")
except Exception as e:
    print(f"❌ Gemini initialization failed: {e}")
    model = None

# Custom JSON encoder for ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

# --- Flask Routes ---
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
          gap: 20px;
      }
      
      @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
      }

      /* 🟢 Sidebar - Made more visible */
      #sidebar {
          width: 250px;
          background: rgba(255, 255, 255, 0.95);
          border-radius: 12px;
          padding: 15px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.2);
          height: 90vh;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          border: 2px solid var(--primary);
      }

      #sidebar h3 {
          text-align: center;
          margin-bottom: 15px;
          color: var(--primary);
      }

      #sidebar button {
          padding: 12px;
          background: var(--primary);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          margin-bottom: 15px;
          font-weight: 500;
          transition: all 0.2s;
      }

      #sidebar button:hover { 
          background: #5a52e0; 
          transform: translateY(-2px);
      }

      #sidebar ul {
          list-style: none;
          padding: 0;
          margin: 0;
          flex: 1;
      }

      #sidebar li {
          padding: 12px;
          margin: 8px 0;
          background: #f8f9fa;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          transition: all 0.2s;
          border-left: 3px solid transparent;
      }

      #sidebar li:hover { 
          background: #e9ecef; 
          border-left: 3px solid var(--primary);
      }
      
      #sidebar li.active {
          background: var(--primary);
          color: white;
          border-left: 3px solid var(--secondary);
      }

      /* 🟢 Chat Container */
      .container {
          flex: 1;
          max-width: 800px;
          margin: 0 auto;
          backdrop-filter: blur(10px);
          background: rgba(255, 255, 255, 0.25);
          border-radius: 20px;
          box-shadow: 0 8px 32px rgba(31, 38, 135, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.18);
          overflow: hidden;
          display: flex;
          flex-direction: column;
      }
      
      h1 {
          text-align: center;
          padding: 20px;
          color: white;
          font-weight: 600;
          text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
      }
      
      #chat {
          flex: 1;
          height: 500px;
          padding: 20px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 15px;
      }
      
      .message {
          max-width: 80%;
          padding: 12px 16px;
          border-radius: 18px;
          line-height: 1.4;
          position: relative;
          animation: fadeIn 0.3s ease;
      }
      
      @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
      }
      
      .user-message {
          align-self: flex-end;
          background: white;
          color: var(--text);
          border-bottom-right-radius: 4px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }
      
      .bot-message {
          align-self: flex-start;
          background: rgba(255, 255, 255, 0.9);
          border-bottom-left-radius: 4px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
      }
      
      .typing {
          display: inline-block;
      }
      
      .typing-dot {
          width: 8px;
          height: 8px;
          background: var(--primary);
          border-radius: 50%;
          display: inline-block;
          margin: 0 2px;
          animation: typing 1.4s infinite ease-in-out;
      }
      
      .typing-dot:nth-child(2) { animation-delay: 0.2s; }
      .typing-dot:nth-child(3) { animation-delay: 0.4s; }
      
      @keyframes typing {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
      }
      
      .input-area {
          display: flex;
          padding: 15px;
          background: rgba(255, 255, 255, 0.3);
          backdrop-filter: blur(5px);
          align-items: center;
      }
      
      #userInput {
          flex: 1;
          padding: 12px 15px;
          border: none;
          border-radius: 12px;
          font-size: 16px;
          outline: none;
          background: rgba(255, 255, 255, 0.9);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      
      #send-btn {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: var(--primary);
          color: white;
          border: none;
          margin-left: 10px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
          position: relative;
          overflow: hidden;
      }
      
      #send-btn:hover {
          background: #5a52e0;
          transform: translateY(-2px);
      }
      
      #send-btn.stop {
          background: var(--danger);
      }
      
      #send-btn svg {
          width: 20px;
          height: 20px;
          transition: all 0.2s;
          position: absolute;
      }
      
      #send-btn .send-icon {
          opacity: 1;
      }
      
      #send-btn .stop-icon {
          opacity: 0;
      }
      
      #send-btn.stop .send-icon {
          opacity: 0;
      }
      
      #send-btn.stop .stop-icon {
          opacity: 1;
      }
      
      #mic-btn {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: var(--danger);
          color: white;
          position: relative;
          margin-left: 10px;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
      }
      
      #mic-btn.listening {
          animation: pulse 1.5s infinite;
      }
      
      @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7); }
          70% { box-shadow: 0 0 0 15px rgba(255, 107, 107, 0); }
          100% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0); }
      }
      
      /* Mobile responsiveness */
      @media (max-width: 600px) {
          body { flex-direction: column; }
          #sidebar { width: 100%; height: auto; margin-bottom: 20px; }
          .container { border-radius: 0; min-height: 100vh; }
          #chat { height: calc(100vh - 150px); }
          .input-area { flex-direction: column; gap: 10px; }
          #send-btn, #mic-btn { width: 100%; margin-left: 0; margin-top: 10px; }
      }
      </style>
    </head>
    <body>
      <div id="sidebar">
        <h3>Chat History</h3>
        <button onclick="startNewChat()">➕ New Chat</button>
        <ul id="sessionList">
          <li class="active" onclick="loadCurrentChat()">💬 Current Chat</li>
        </ul>
      </div>

      <div class="container">
        <h1>🤖 HealthQ AI Assistant</h1>
        <div id="chat">
          <div class="message bot-message">
            Hi there! How can I help you today? 🌤 Note: I am not a doctor. Please consult a healthcare professional for serious concerns.
          </div>
        </div>
        <div class="input-area">
          <input id="userInput" type="text" placeholder="Ask a health question..." autocomplete="off"/>
          <button id="send-btn" onclick="handleSend()">
            <svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"></path>
            </svg>
            <svg class="stop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1" stroke-width="2"></rect>
            </svg>
          </button>
          <button id="mic-btn" onclick="startListening()">🎤</button>
        </div>
      </div>

      <script>
        const chat = document.getElementById("chat");
        const sendBtn = document.getElementById("send-btn");
        let controller = null;
        let isGenerating = false;
        let currentSessionId = null;
        
        async function handleSend() {
          if (isGenerating) {
            stopGeneration();
          } else {
            await sendMessage();
          }
        }
        
        async function sendMessage(userText = null) {
          const input = document.getElementById("userInput");
          if (!userText) userText = input.value.trim();
          if (!userText) return;
          
          addMessage(userText, "user-message");
          input.value = "";
          
          const typingId = showTyping();
          toggleSendButton(true);
          isGenerating = true;
          
          try {
            controller = new AbortController();
            const res = await fetch("/chat", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ message: userText, session_id: currentSessionId }),
              signal: controller.signal
            });
            
            removeTyping(typingId);
            const botDiv = document.createElement("div");
            botDiv.classList.add("message", "bot-message");
            chat.appendChild(botDiv);
            chat.scrollTop = chat.scrollHeight;

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let partial = "";

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              partial += decoder.decode(value, { stream: true });
              botDiv.innerHTML = partial;
              chat.scrollTop = chat.scrollHeight;
            }
            
            // Refresh chat history after new message
            await loadChatHistory();
          } catch (error) {
            if (error.name !== 'AbortError') {
              removeTyping(typingId);
              addMessage("⚠️ Failed to get response. Please try again.", "bot-message");
            }
          } finally {
            toggleSendButton(false);
            isGenerating = false;
            controller = null;
          }
        }
        
        function stopGeneration() {
          if (controller) controller.abort();
          toggleSendButton(false);
          isGenerating = false;
          document.querySelectorAll('[id^="typing-"]').forEach(el => el.remove());
        }
        
        function toggleSendButton(isGenerating) {
          sendBtn.classList.toggle("stop", isGenerating);
        }
        
        function addMessage(text, className) {
          const messageDiv = document.createElement("div");
          messageDiv.classList.add("message", className);
          messageDiv.innerHTML = text;
          chat.appendChild(messageDiv);
          chat.scrollTop = chat.scrollHeight;
        }
        
        function showTyping() {
          const typingId = "typing-" + Date.now();
          const typingDiv = document.createElement("div");
          typingDiv.classList.add("message", "bot-message");
          typingDiv.id = typingId;
          typingDiv.innerHTML = `
            <div class="typing">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
          `;
          chat.appendChild(typingDiv);
          chat.scrollTop = chat.scrollHeight;
          return typingId;
        }
        
        function removeTyping(id) {
          const typingElement = document.getElementById(id);
          if (typingElement) typingElement.remove();
        }
        
        // Voice recognition
        function startListening() {
          const micBtn = document.getElementById("mic-btn");
          if (!('webkitSpeechRecognition' in window)) {
            alert("Speech recognition requires Chrome browser.");
            return;
          }
          const recognition = new webkitSpeechRecognition();
          recognition.lang = "en-US";
          recognition.interimResults = false;
          micBtn.classList.add("listening");
          recognition.start();
          recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById("userInput").value = transcript;
          };
          recognition.onerror = (event) => { console.error("Speech error:", event.error); };
          recognition.onend = () => { micBtn.classList.remove("listening"); };
        }
        
        document.getElementById("userInput").addEventListener("keypress", (e) => {
          if (e.key === "Enter" && !isGenerating) handleSend();
        });

        // 🟢 Load chat history
        async function loadChatHistory() {
          try {
            const res = await fetch("/history");
            const data = await res.json();
            const list = document.getElementById("sessionList");
            
            // Keep the "Current Chat" item
            const currentChatItem = list.querySelector('li:first-child');
            list.innerHTML = '';
            list.appendChild(currentChatItem);
            
            // Add history items
            data.forEach((chatItem, idx) => {
              const li = document.createElement("li");
              const preview = chatItem.user ? (chatItem.user.substring(0, 20) + (chatItem.user.length > 20 ? "..." : "")) : "Chat " + (idx+1);
              li.textContent = "💬 " + preview;
              li.onclick = () => loadHistory(chatItem);
              list.appendChild(li);
            });
          } catch (error) {
            console.error("Error loading chat history:", error);
          }
        }

        function loadHistory(chatItem) {
          chat.innerHTML = "";
          if (chatItem.user) {
            addMessage(chatItem.user, "user-message");
          }
          if (chatItem.bot) {
            addMessage(chatItem.bot.replace(/\\n/g, "<br>"), "bot-message");
          }
          currentSessionId = chatItem._id;
          
          // Update active state
          document.querySelectorAll("#sessionList li").forEach(item => {
            item.classList.remove("active");
          });
          event.target.classList.add("active");
        }

        function loadCurrentChat() {
          chat.innerHTML = "";
          addMessage("Hi there! How can I help you today? 🌤 Note: I am not a doctor. Please consult a healthcare professional for serious concerns.", "bot-message");
          currentSessionId = null;
          
          // Update active state
          document.querySelectorAll("#sessionList li").forEach(item => {
            item.classList.remove("active");
          });
          document.querySelector("#sessionList li:first-child").classList.add("active");
        }

        function startNewChat() {
          loadCurrentChat();
        }

        // 🟢 Fetch chat history when page loads
        window.onload = function() {
          loadChatHistory();
        };
      </script>
    </body>
    </html>
    """
    return render_template_string(HTML_TEMPLATE)

@app.route("/chat", methods=["POST"])
def chat():
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

            # Save to database if MongoDB is available
            if chats_collection is not None:
                try:
                    chat_data = {
                        "user": user_msg,
                        "bot": response_text,
                        "timestamp": datetime.now()
                    }
                    
                    if session_id:
                        # Update existing conversation
                        chats_collection.update_one(
                            {"_id": ObjectId(session_id)},
                            {"$set": chat_data}
                        )
                    else:
                        # Create new conversation
                        result = chats_collection.insert_one(chat_data)
                        # Return the new session ID
                        yield f"<script>currentSessionId = '{result.inserted_id}';</script>"
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    yield ""

        except Exception as e:
            yield f"⚠️ Error: {str(e)}"

    return Response(generate(), mimetype="text/plain")

@app.route("/history", methods=["GET"])
def history():
    try:
        if chats_collection is not None:
            chats = list(chats_collection.find().sort("timestamp", -1).limit(10))
            return jsonify(chats)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify([])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
