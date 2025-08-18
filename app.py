import os
from flask import Flask, request, jsonify, render_template_string, Response
import google.generativeai as genai

# ----------------------------
# Gemini API Setup
# ----------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyC-0i3sof8_6HMTmiv9Xtx3I-Oa6rDasXc"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ----------------------------
# Flask App
# ----------------------------
app = Flask(__name__)

# ----------------------------
# Frontend (HTML + CSS + JS)
# ----------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HealthQ - AI Powered Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    #app { width: 90%; max-width: 800px; background: white; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); display: flex; flex-direction: column; height: 90vh; overflow: hidden; }
    #header { background: #2563eb; color: white; text-align: center; padding: 15px; font-size: 20px; font-weight: bold; }
    #chat { flex: 1; padding: 20px; overflow-y: auto; border-bottom: 1px solid #eee; }
    .msg { margin: 10px 0; }
    .user { color: #2563eb; font-weight: bold; }
    .bot { color: #16a34a; font-weight: bold; }
    .bubble { padding: 10px 14px; border-radius: 10px; display: inline-block; max-width: 80%; }
    .user .bubble { background: #e0edff; align-self: flex-end; }
    .bot .bubble { background: #e8f9f0; align-self: flex-start; }
    #controls { display: flex; align-items: center; padding: 10px; border-top: 1px solid #eee; }
    #message { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
    button { margin-left: 8px; padding: 10px 15px; border: none; border-radius: 8px; cursor: pointer; transition: box-shadow 0.2s ease; }
    button:active, button.glow { box-shadow: 0 0 10px rgba(0,0,0,0.4); }
    #sendBtn { background: #2563eb; color: white; }
    #stopBtn { background: red; color: white; }
    #micBtn { background: #16a34a; color: white; }
    #imageInput { display: none; }
    #uploadBtn { background: #f59e0b; color: white; }
  </style>
</head>
<body>
  <div id="app">
    <div id="header">HealthQ - AI Powered Chatbot</div>
    <div id="chat"></div>
    <div id="controls">
      <input type="text" id="message" placeholder="Type a message...">
      <button id="micBtn">🎤</button>
      <button id="sendBtn">Send</button>
      <button id="stopBtn">Stop</button>
      <input type="file" id="imageInput" accept="image/*">
      <button id="uploadBtn">📷</button>
    </div>
  </div>

  <script>
    const chat = document.getElementById("chat");
    const msgInput = document.getElementById("message");
    const sendBtn = document.getElementById("sendBtn");
    const stopBtn = document.getElementById("stopBtn");
    const micBtn = document.getElementById("micBtn");
    const uploadBtn = document.getElementById("uploadBtn");
    const imageInput = document.getElementById("imageInput");

    let controller = null;

    function glowButton(btn) {
      btn.classList.add("glow");
      setTimeout(() => btn.classList.remove("glow"), 300);
    }

    function appendMessage(sender, text) {
      const div = document.createElement("div");
      div.className = "msg " + sender;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = text;
      div.appendChild(bubble);
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
      return bubble;
    }

    async function sendMessage(imageFile=null) {
      const text = msgInput.value.trim();
      if (!text && !imageFile) return;
      if (text) appendMessage("user", text);
      if (imageFile) appendMessage("user", "[📷 Uploaded Image]");

      msgInput.value = "";
      glowButton(sendBtn);

      controller = new AbortController();
      const signal = controller.signal;

      const formData = new FormData();
      formData.append("message", text);
      if (imageFile) formData.append("image", imageFile);

      try {
        const response = await fetch("/chat", {
          method: "POST",
          body: formData,
          signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let botBubble = appendMessage("bot", "");
        let fullText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          fullText += chunk;
          botBubble.textContent = fullText;
          chat.scrollTop = chat.scrollHeight;
        }
      } catch (err) {
        appendMessage("bot", "[Stopped or error]");
      }
    }

    sendBtn.onclick = () => sendMessage();
    msgInput.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });

    stopBtn.onclick = () => {
      glowButton(stopBtn);
      if (controller) controller.abort();
    };

    // 🎤 Microphone
    micBtn.onclick = () => {
      glowButton(micBtn);
      if (!("webkitSpeechRecognition" in window)) {
        alert("Speech recognition not supported in this browser.");
        return;
      }
      const recognition = new webkitSpeechRecognition();
      recognition.lang = "en-US";
      recognition.start();
      recognition.onresult = (event) => {
        msgInput.value = event.results[0][0].transcript;
      };
    };

    // 📷 Image upload
    uploadBtn.onclick = () => { glowButton(uploadBtn); imageInput.click(); };
    imageInput.onchange = () => {
      if (imageInput.files.length > 0) {
        sendMessage(imageInput.files[0]);
      }
    };
  </script>
</body>
</html>
"""

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.form.get("message", "")
    image = request.files.get("image")

    def generate():
        try:
            if image:
                img_bytes = image.read()
                response = model.generate_content(
                    [user_message, {"mime_type": "image/png", "data": img_bytes}],
                    stream=True,
                )
            else:
                response = model.generate_content(user_message, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"[Error: {str(e)}]"

    return Response(generate(), content_type="text/plain")

# ----------------------------
# Run Flask App
# ----------------------------
if __name__ == "__main__":
    print("🚀 Running at http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
