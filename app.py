from flask import Flask, request, jsonify, render_template_string
import google.generativeai as genai
import os

app = Flask(__name__)

# ✅ Replace with your actual Gemini API key
GEMINI_API_KEY = "AIzaSyC-0i3sof8_6HMTmiv9Xtx3I-Oa6rDasXc"
genai.configure(api_key=GEMINI_API_KEY)

# Load Gemini model
model = genai.GenerativeModel("gemini-pro")

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gemini Chatbot</title>
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
            h2 {
                color: #333;
            }
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
            button:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <h2>🤖 Chat with Gemini AI</h2>
        <div id="chat-box"></div>
        <form id="chat-form">
            <input type="text" id="message" placeholder="Type your message..." autocomplete="off" required />
            <button type="submit">Send</button>
        </form>
        <script>
            const form = document.getElementById('chat-form');
            const chatBox = document.getElementById('chat-box');
            const messageInput = document.getElementById('message');

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
                    appendMessage('Gemini', "Error fetching response.");
                }
            };

            function appendMessage(sender, message) {
                const div = document.createElement('div');
                div.innerHTML = `<strong>${sender}:</strong> ${message}`;
                chatBox.appendChild(div);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")

    try:
        response = model.generate_content(user_input)
        reply = response.text.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
