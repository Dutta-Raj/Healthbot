from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI
client = OpenAI(api_key="your-api-key-here")

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Chatbot</title>
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
        <h2>🤖 Chat with AI</h2>
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
                    appendMessage('AI', data.reply || data.error);
                } catch (err) {
                    appendMessage('AI', "Error fetching response.");
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
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
