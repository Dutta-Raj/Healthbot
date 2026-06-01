# 🏥 MediBot AI - Intelligent Medical Assistant

> **Evolution:** Migrated from **Flask + Gemini** to **FastAPI + Cohere + RAG + Kafka** for better performance, scalability, and features.

A production-ready Medical Chatbot with RAG (Retrieval-Augmented Generation), Kafka Event-Driven Architecture, Cohere AI, and MongoDB Atlas.

⚠️ **Medical Disclaimer**: Informational only. Consult healthcare professionals for medical advice.

---

## 🔄 Migration Journey: Flask → FastAPI

| Aspect | Before (Flask) | After (FastAPI) |
|--------|----------------|-----------------|
| Framework | Flask | FastAPI (async, faster) |
| AI Model | Gemini | Cohere (better medical responses) |
| Knowledge Retrieval | None | RAG (ChromaDB) |
| Message Queue | None | Kafka (event-driven) |
| Response Speed | Slow (3-5 sec) | Fast (<1 sec streaming) |
| Authentication | Basic | JWT + bcrypt |
| Conversation Memory | None | Full context memory |
| Frontend | Basic HTML | 3D Modern UI |
| Deployment | Manual | CI/CD (GitHub Actions + Render) |

---

## ✨ Features

- 🧠 **RAG** - Medical knowledge retrieval from vector database (ChromaDB)
- 📨 **Kafka** - Event-driven message queuing for scalability
- 🤖 **Cohere AI** - Intelligent, conversational medical responses
- 🔐 **JWT Authentication** - Secure login/register with bcrypt
- 💾 **MongoDB Atlas** - Cloud database for conversations & users
- 📚 **Conversation Memory** - Remembers context for follow-ups
- 🚨 **Emergency First Aid** - Real-time emergency guidance
- 🎨 **3D Modern UI** - Stunning 3D background with streaming responses
- 🔄 **CI/CD Pipeline** - GitHub Actions for automated testing
- ⏹️ **Stop/Continue** - Pause and resume response generation

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| Backend | FastAPI, Python 3.10+ |
| Database | MongoDB Atlas |
| Vector DB (RAG) | ChromaDB |
| AI/LLM | Cohere API |
| Message Queue | Apache Kafka |
| Authentication | JWT + bcrypt |
| Frontend | HTML/CSS/JS + Three.js (3D) |
| CI/CD | GitHub Actions |
| Deployment | Render |

---

## 📁 Project Structure
Healthbot/
├── main.py # Main FastAPI application
├── index.html # 3D frontend interface
├── kafka_integration.py # Kafka producer/consumer
├── requirements.txt # Python dependencies
├── render.yaml # Render deployment config
├── .github/workflows/ci.yml # CI/CD pipeline
├── Dockerfile # Docker configuration
├── docker-compose.yml # Docker Compose with Kafka
└── README.md # Documentation

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
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys

# Run application
python main.py
