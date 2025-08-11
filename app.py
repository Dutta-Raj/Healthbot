from flask import Flask, request, jsonify, render_template_string
from database import db, User, ChatHistory
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env (local only)
load_dotenv()

app = Flask(__name__)

# Database config (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///chatbot.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Ensure DB tables exist
with app.app_context():
    db.create_all()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not set in environment variables.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gemini AI Health Chatbot</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f9;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            h2 { color: #333; }
            #chat-box {
                width: 90%;
                max-width: 600px;
                height: 400px;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 10px;
                overflow-y: auto;
                background-color: white;
                margin-bottom: 10px;
            }
            #chat-form {
                display: flex;
                gap: 10px;
                width: 90%;
                max-width: 600px;
            }
            #message {
                flex: 1;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ccc;
                font-size: 16px;
            }
            button {
                padding: 10px 20px;
                border: none;
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <h2>🤖 Gemini Health Chatbot</h2>
        <div id="chat-box"></div>
        <form id="chat-form">
            <input type="text" id="message" placeholder="Type your message..." autocomplete="off" required />
            <button type="submit">Send</button>
        </form>
        <script>
            const form = document.getElementById('chat-form');
            const chatBox = document.getElementById('chat-box');
            const messageInput = document.getElementById('message');

            async function loadHistory() {
                const res = await fetch("/history");
                const data = await res.json();
                data.forEach(msg => appendMessage(msg.sender, msg.message));
            }

            form.onsubmit = async (e) => {
                e.preventDefault();
                const userMessage = messageInput.value.trim();
                if (!userMessage) return;

                appendMessage('You', userMessage);
                messageInput.value = '';
                try {
                    const res = await fetch("/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ message: userMessage })
                    });
                    const data = await res.json();
                    appendMessage('Gemini', data.reply || data.error);
                } catch (err) {
                    appendMessage('Gemini', "⚠️ Error: Unable to fetch response.");
                }
            };

            function appendMessage(sender, message) {
                const div = document.createElement('div');
                div.innerHTML = `<strong>${sender}:</strong> ${message}`;
                chatBox.appendChild(div);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            loadHistory();
        </script>
    </body>
    </html>
    """)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")

    try:
        # Save user message
        user = User.query.first()
        if not user:
            user = User(username="default_user")
            db.session.add(user)
            db.session.commit()

        db.session.add(ChatHistory(user_id=user.id, message=user_input, sender="user"))

        # Get Gemini response
        response = model.generate_content(user_input)
        bot_reply = response.text.strip()

        # Save bot message
        db.session.add(ChatHistory(user_id=user.id, message=bot_reply, sender="bot"))
        db.session.commit()

        return jsonify({"reply": bot_reply})
    except Exception as e:
        return jsonify({"error": f"❌ {str(e)}"}), 500

@app.route("/history")
def history():
    user = User.query.first()
    if not user:
        return jsonify([])
    messages = ChatHistory.query.filter_by(user_id=user.id).order_by(ChatHistory.timestamp).all()
    return jsonify([{"sender": msg.sender, "message": msg.message} for msg in messages])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
