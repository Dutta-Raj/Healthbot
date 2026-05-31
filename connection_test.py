# connection_test.py
"""Complete system connection test"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("SYSTEM CONNECTION DIAGNOSTIC")
print("="*60)

results = {"pass": 0, "fail": 0, "warn": 0}

# 1. MongoDB Atlas Test
print("\n[1] MONGODB ATLAS CONNECTION")
print("-" * 40)
try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        print("  ❌ No MongoDB URI in .env")
        results["fail"] += 1
    else:
        print(f"  URI: {mongo_uri[:50]}...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        db_name = os.getenv('DATABASE_NAME', 'healthbot')
        db = client[db_name]
        
        print(f"  ✅ MongoDB Atlas CONNECTED")
        print(f"  Database: {db_name}")
        
        # Check collections
        collections = db.list_collection_names()
        print(f"  Collections: {', '.join(collections) if collections else 'none'}")
        
        # Check users collection
        if 'users' in collections:
            user_count = db.users.count_documents({})
            print(f"  Users in database: {user_count}")
        
        results["pass"] += 1
except Exception as e:
    print(f"  ❌ MongoDB Error: {str(e)[:100]}")
    results["fail"] += 1

# 2. Cohere AI Test
print("\n[2] COHERE AI CONNECTION")
print("-" * 40)
try:
    import cohere
    api_key = os.getenv('COHERE_API_KEY')
    if api_key:
        co = cohere.Client(api_key=api_key)
        print(f"  ✅ Cohere API Key found")
        
        # Quick test
        response = co.chat(
            message="Say 'OK'",
            model="command-a-03-2025",
            max_tokens=5
        )
        if response and response.text:
            print(f"  ✅ Cohere AI RESPONDING")
            results["pass"] += 1
    else:
        print("  ❌ No Cohere API key")
        results["fail"] += 1
except Exception as e:
    print(f"  ⚠️ Cohere warning: {str(e)[:80]}")
    results["warn"] += 1

# 3. Kafka Test
print("\n[3] KAFKA CONNECTION")
print("-" * 40)
kafka_enabled = os.getenv('KAFKA_ENABLED', 'false').lower() == 'true'
if kafka_enabled:
    try:
        from kafka import KafkaProducer
        bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            request_timeout_ms=5000,
            max_block_ms=5000
        )
        producer.close()
        print(f"  ✅ Kafka CONNECTED at {bootstrap}")
        results["pass"] += 1
    except Exception as e:
        print(f"  ⚠️ Kafka not available: {str(e)[:80]}")
        print(f"  ℹ️  Set KAFKA_ENABLED=false in .env to disable")
        results["warn"] += 1
else:
    print(f"  ℹ️  Kafka DISABLED (KAFKA_ENABLED=false)")
    print(f"  ✅ Not required for chatbot operation")

# 4. API Server Test
print("\n[4] API SERVER STATUS")
print("-" * 40)
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ API Server RUNNING")
        print(f"  Status: {data.get('status', 'unknown')}")
        print(f"  Database: {data.get('database', 'unknown')}")
        print(f"  AI: {data.get('ai', 'unknown')}")
        results["pass"] += 1
    else:
        print(f"  ⚠️ API returned {response.status_code}")
        results["warn"] += 1
except Exception as e:
    print(f"  ❌ API Server NOT RESPONDING")
    print(f"  Start server: python healthbot_final.py")
    results["fail"] += 1

# 5. Environment Variables Check
print("\n[5] ENVIRONMENT CONFIGURATION")
print("-" * 40)
required_vars = ['MONGODB_URI', 'COHERE_API_KEY', 'SECRET_KEY']
for var in required_vars:
    val = os.getenv(var)
    if val and val not in ['your_key_here', 'your-secret-key']:
        print(f"  ✅ {var}: configured")
    else:
        print(f"  ❌ {var}: MISSING or invalid")
        results["fail"] += 1

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"  ✅ PASS: {results['pass']}")
print(f"  ⚠️ WARN: {results['warn']}")
print(f"  ❌ FAIL: {results['fail']}")

if results['fail'] == 0:
    print("\n🎉 ALL SYSTEMS OPERATIONAL!")
    print("   Your HealthBot AI is ready to use!")
elif results['fail'] <= 2:
    print("\n⚠️ Minor issues detected but system may still work")
else:
    print("\n❌ Multiple failures detected. Please check configuration")

print("="*60)
