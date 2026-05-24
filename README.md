[![CI/CD Pipeline](https://github.com/Dutta-Raj/Healthbot/actions/workflows/ci.yml/badge.svg)](https://github.com/Dutta-Raj/Healthbot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen.svg)](https://www.mongodb.com/cloud/atlas)
[![Kafka](https://img.shields.io/badge/Kafka-Event%20Driven-black.svg)](https://kafka.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# 🤖 HealthBot - AI Health Assistant

**HealthBot** is an advanced AI-powered health assistant built with **Flask**, **Cohere AI**, and **MongoDB Atlas** that provides intelligent health conversations with proper medical safety features.

> ⚠️ **Medical Disclaimer**: This application provides informational responses only. Always consult qualified healthcare professionals for medical advice, diagnosis, or treatment.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💬 **AI Health Chat** | Smart responses using Cohere AI with medical safety guardrails |
| 📅 **30-Day Chat History** | Access previous conversations with daily auto-sessions |
| 🆕 **New Chat Sessions** | Start fresh conversations anytime |
| 🔐 **User Authentication** | Secure JWT-based login/register system |
| ⚠️ **Medical Disclaimers** | Always routes users to professionals for serious conditions |
| 🚀 **Kafka Integration** | Event-driven message queuing for async processing |
| 🔄 **CI/CD Pipeline** | Automated testing and deployment via GitHub Actions |
| 🎨 **Beautiful UI** | Modern gradient design with responsive layout |

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | Flask, Python 3.10 |
| **Database** | MongoDB Atlas |
| **AI/LLM** | Cohere API |
| **Message Queue** | Apache Kafka |
| **Authentication** | JWT (JSON Web Tokens) |
| **Testing** | Pytest, unittest |
| **CI/CD** | GitHub Actions |
| **Deployment** | Render |

---

## 📁 Project Structure
Healthbot/
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── kafka_service.py # Kafka event producer/consumer
├── health_alerts.py # Health alert utilities
├── register_usre.py # User registration logic
├── test_app_fixed.py # Unit tests
├── test_kafka.py # Kafka integration tests
└── .github/workflows/
└── ci.yml # CI/CD pipeline configuration

text

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- MongoDB Atlas account
- Cohere API key
- Kafka broker (local or cloud)

### Steps

1. **Clone the repository**
```bash
git clone https://github.com/Dutta-Raj/Healthbot.git
cd Healthbot
Create virtual environment

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies

bash
pip install -r requirements.txt
Set environment variables

bash
export MONGO_URI="your_mongodb_connection_string"
export COHERE_API_KEY="your_cohere_api_key"
export JWT_SECRET_KEY="your_jwt_secret"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
Run the application

bash
python app.py
Run tests

bash
python test_app_fixed.py
