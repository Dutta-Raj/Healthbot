import os
from flask import Flask, render_template_string, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

api_key = os.getenv("Generative Language API Key", "AIzaSyDG06Ss81YRT8XpqQrUmX0A4W4Bjk_XvBk")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

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
    }
    
    @keyframes gradient {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    
    .container {
      max-width: 800px;
      margin: 0 auto;
      backdrop-filter: blur(10px);
      background: rgba(255, 255, 255, 0.25);
      border-radius: 20px;
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.18);
      overflow: hidden;
    }
    
    h1 {
      text-align: center;
      padding: 20px;
      color: white;
      font-weight: 600;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    #chat {
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
      .container {
        border-radius: 0;
        min-height: 100vh;
      }
      
      #chat {
        height: calc(100vh - 150px);
      }
      
      .input-area {
        flex-direction: column;
        gap: 10px;
      }
      
      #send-btn, #mic-btn {
        width: 100%;
        margin-left: 0;
        margin-top: 10px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🤖 HealthQ AI Assistant</h1>
    
    <div id="chat"></div>
    
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
      
      // Display user message
      addMessage(userText, "user-message");
      input.value = "";
      
      // Show typing indicator
      const typingId = showTyping();
      toggleSendButton(true);
      isGenerating = true;
      
      try {
        controller = new AbortController();
        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userText }),
          signal: controller.signal
        });
        
        const data = await res.json();
        removeTyping(typingId);
        addMessage(data.reply, "bot-message");
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
      if (controller) {
        controller.abort();
      }
      toggleSendButton(false);
      isGenerating = false;
      
      // Remove any active typing indicators
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
      
      recognition.onerror = (event) => {
        console.error("Speech error:", event.error);
      };
      
      recognition.onend = () => {
        micBtn.classList.remove("listening");
      };
    }
    
    // Allow Enter key to send message
    document.getElementById("userInput").addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !isGenerating) {
        handleSend();
      }
    });
  </script>
</body>
</html>
"""

@app.route("/")
def home():
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
    app.run(host='0.0.0.0', port=5000, debug=True)
