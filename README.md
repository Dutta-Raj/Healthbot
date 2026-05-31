# 🏥 MediBot AI - Intelligent Medical Assistant

A production-ready Medical Chatbot with RAG, Kafka Event-Driven Architecture, Cohere AI, and MongoDB Atlas.

> ⚠️ **Medical Disclaimer**: Informational only. Consult healthcare professionals for medical advice.

---

## ✨ Features

- 🧠 **RAG** - Medical knowledge retrieval from vector database
- 📨 **Kafka** - Event-driven message queuing
- 🤖 **Cohere AI** - Intelligent medical responses
- 🔐 **JWT Authentication** - Secure login/register
- 💾 **MongoDB Atlas** - Cloud database storage
- 📚 **Conversation Memory** - Remembers context for follow-ups
- 🚨 **Emergency First Aid** - Real-time guidance
- 🎨 **Modern UI** - Streaming responses with stop/continue

---

## 🛠️ Tech Stack


| Category | Technologies |
|----------|--------------|
| **Backend** | FastAPI, Python 3.10+ |
| **Database** | MongoDB Atlas |
| **Vector DB** | ChromaDB |
| **AI/LLM** | Cohere API |
| **Message Queue** | Apache Kafka |
| **Authentication** | JWT + bcrypt |
| **Frontend** | HTML/CSS/JS + Three.js (3D) |
| **CI/CD** | GitHub Actions |
| **Deployment** | Render |
---

## 📁 Project Structure
Healthbot/
├── main.py # Main FastAPI app
├── start.bat # Quick launcher
├── README.md
├── LICENSE
│
├── src/
│ ├── backend/ # Python backend files
│ ├── frontend/ # HTML frontend
│ └── kafka/ # Kafka integration
│
├── config/
│ ├── .env # Environment (gitignored)
│ ├── .env.example # Example config
│ └── requirements.txt # Dependencies
│
├── scripts/ # Utility scripts
└── tests/ # Test files

text

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Dutta-Raj/Healthbot.git
cd Healthbot

# Create virtual environment
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Mac/Linux

# Install dependencies
pip install -r config/requirements.txt

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your keys

# Run application
python main.py
