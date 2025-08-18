import os
from flask import Flask, render_template_string, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Try to get API key from environment variable, else fallback to placeholder
api_key = os.getenv("Generative Language API Key", "AIzaSyDG06Ss81YRT8XpqQrUmX0A4W4Bjk_XvBk")
genai.configure(api_key=api_key)

# Initialize Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Frontend with futuristic UI + mic
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>🤖 HealthQ - AI Health Assistant </title>
  <style>
    body { 
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
      background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); 
      color: white; 
      text-align: center; 
      padding: 20px; 
    }
    h1 { 
      color: #00f7ff; 
      text-shadow: 0 0 10px #00f7ff, 0 0 20px #00aaff; 
    }
    #chat { 
      max-width: 600px; 
      margin: auto; 
      background: rgba(0,0,0,0.5); 
      border-radius: 15px; 
      padding: 20px; 
      box-shadow: 0 0 15px rgba(0,255,255,0.3); 
      height: 400px;
      overflow-y: auto;
    }
    .user { 
      text-align: right; 
      color: #00ffcc; 
      margin: 10px; 
    }
    .bot { 
      text-align: left; 
      background: #00f7ff; 
      color: black; 
      margin: 10px; 
      padding: 10px; 
      border-radius: 10px; 
      display: inline-block; 
      max-width: 80%;
    }
    .input-area {
      margin-top: 15px;
      display: flex;
      justify-content: center;
      gap: 10px;
    }
    input { 
      width: 70%; 
      padding: 10px; 
      border-radius: 8px; 
      border: none; 
      outline: none;
    }
    button { 
      padding: 10px 20px; 
      border: none; 
      border-radius: 8px; 
      background: #00f7ff; 
      color: black; 
      cursor: pointer; 
      font-weight: bold;
    }
    button:hover { background: #00c3ff; }
    #mic-btn {
      width: 50px; 
      height: 50px; 
      border-radius: 50%; 
      background: #ff005c; 
      color: white; 
      border: none;
      cursor: pointer;
      font-size: 20px;
      box-shadow: 0 0 15px #ff005c;
    }
    #mic-btn.listening {
      background: #00ff88;
      box-shadow: 0 0 20px #00ff88;
    }
  </style>
</head>
<body>
  <h1>🤖 HealthQ - AI Health Assistant</h1>
  <div id="chat"></div>

  <div class="input-area">
    <input id="userInput" type="text" placeholder="Ask a health question..."/>
    <button onclick="sendMessage()">Send</button>
    <button id="mic-btn" onclick="startListening()">🎤</button>
  </div>

  <script>
    async function sendMessage(userText=null) {
      let input = document.getElementById("userInput");
      let chat = document.getElementById("chat");
      if (!userText) userText = input.value.trim();
      if (!userText) return;

      // Display user message
      chat.innerHTML += `<div class='user'>${userText}</div>`;
      input.value = "";

      // Send request to backend
      let res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
      });
      let data = await res.json();

      // Display bot response
      chat.innerHTML += `<div class='bot'>${data.reply}</div>`;
      chat.scrollTop = chat.scrollHeight;
    }

    // 🎤 Voice recognition
    function startListening() {
      const micBtn = document.getElementById("mic-btn");

      if (!('webkitSpeechRecognition' in window)) {
        alert("Your browser does not support Speech Recognition. Try Chrome.");
        return;
      }

      const recognition = new webkitSpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.continuous = false;

      micBtn.classList.add("listening");

      recognition.start();

      recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById("userInput").value = transcript;
        sendMessage(transcript);
      };

      recognition.onerror = function(event) {
        console.error("Speech recognition error:", event);
      };

      recognition.onend = function() {
        micBtn.classList.remove("listening");
      };
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message")
    try:
        response = model.generate_content(user_msg)
        bot_reply = response.text + "\n\n⚠️ Note: I am not a doctor. Please consult a healthcare professional for serious concerns."
    except Exception as e:
        bot_reply = f"⚠️ Error: {str(e)}"
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(debug=True)
