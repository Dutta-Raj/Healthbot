from flask import Flask, request, jsonify
from transformers import pipeline

app = Flask(__name__)

# Load a pre-trained model (simple QnA model)
chatbot = pipeline("conversational", model="microsoft/DialoGPT-medium")

@app.route("/", methods=["GET"])
def home():
    return "🤖 Hello! Chatbot is running."

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "No message provided."}), 400

    response = chatbot(user_input)
    return jsonify({"response": response[0]['generated_responses'][0]})
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
