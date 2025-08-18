from flask import Flask, render_template_string, request, jsonify
import google.generativeai as genai
import os
import speech_recognition as sr

# Flask app setup
app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key="AIzaSyC-0i3sof8_6HMTmiv9Xtx3I-Oa6rDasXc")
model = genai.GenerativeModel("gemini-pro")

# Store active requests
stop_generation = False

# HTML + CSS + JS Frontend
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HealthQ - AI Powered Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f6f9; display: flex; justify-content: center; }
    .chat-container { width: 65%; background: #fff; margin-top: 30px; border-radius: 12px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1); overflow: hidden; }
    .chat-header { background: #1a73e8; padding: 15px; text-align: center; color: white; font-size: 22px; font-weight: bold; }
    .chat-box { height: 500px; overflow-y: auto; padding: 20px; }
    .msg { margin: 10px 0; padding: 12px; border-radius: 12px; max-width: 70%; }
    .user { background: #e3f2fd; align-self: flex-end; text-align: right; }
    .bot { background: #e6f4ea; color: #0b8043; align-self: flex-start; }
    .chat-input { display: flex; padding: 12px; border-top: 1px solid #ddd; background: #fafafa; }
    .chat-input input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #ddd; }
    .chat-input button { margin-left: 10px; padding: 10px 16px; border: none; border-radius: 8px; cursor: pointer; }
    .send { background: #1a73e8; color: white; }
    .stop { background: #ea4335; color: white; }
    .mic { background: #34a853; color: white; }
    .upload { background: #fbbc04; color: white; }
    .msg-wrapper { display: flex; flex-direction: column; }
  </style>
</head>
<body>
  <div class="chat-container">
    <div class="chat-header">HealthQ - AI Powered Chatbot</div>
    <div id="chat-box" class="chat-box"></div>
    <div class="chat-input">
      <input id="user-input" type="text" placeholder="Type a message...">
      <button class="mic" onclick="startMic()">🎤</button>
      <button class="send" onclick="sendMessage()">Send</button>
      <button class="stop" onclick="stopMessage()">Stop</button>
      <input type="file" id="file-input" style="display:none;" onchange="uploadImage(event)">
      <button class="upload" onclick="document.getElementById('file-input').click()">📷</button>
    </div>
  </div>

<script>
async function sendMessage() {
  let input = document.getElementById("user-input");
  let message = input.value;
  if (!message) return;
  appendMessage("user", message);
  input.value = "";

  let response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  let data = await response.json();
  appendMessage("bot", data.reply);
}

async function stopMessage() {
  await fetch("/stop", { method: "POST" });
  appendMessage("bot", "[Stopped current response]");
}

function appendMessage(sender, text) {
  let chatBox = document.getElementById("chat-box");
  let msg = document.createElement("div");
  msg.className = "msg " + sender;
  msg.innerText = text;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function uploadImage(event) {
  let file = event.target.files[0];
  let formData = new FormData();
  formData.append("file", file);

  appendMessage("user", "[📷 Uploaded Image]");
  
  let response = await fetch("/upload", { method: "POST", body: formData });
  let data = await response.json();
  appendMessage("bot", data.reply);
}

// 🎤 Speech Recognition
function startMic() {
  let recognition = new webkitSpeechRecognition();
  recognition.lang = "en-US";
  recognition.onresult = function(event) {
    let text = event.results[0][0].transcript;
    document.getElementById("user-input").value = text;
  };
  recognition.start();
}
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/chat", methods=["POST"])
def chat():
    global stop_generation
    stop_generation = False
    data = request.json
    user_msg = data.get("message", "")

    if stop_generation:
        return jsonify({"reply": "[Stopped]"})

    try:
        response = model.generate_content(user_msg)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"[Error: {str(e)}]"})

@app.route("/stop", methods=["POST"])
def stop():
    global stop_generation
    stop_generation = True
    return jsonify({"reply": "Stopped response"})

@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]
        filepath = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)
        file.save(filepath)

        # ✅ Reopen file safely for Gemini
        with open(filepath, "rb") as f:
            response = model.generate_content(["Describe this image", f])
        
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"[Error: {str(e)}]"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
