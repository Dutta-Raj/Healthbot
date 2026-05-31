# verify_ai.py
"""Verify Cohere AI is working"""

import requests
import time

print("\n" + "="*60)
print("TESTING AI CHATBOT")
print("="*60)

# Test queries that should get AI responses
test_queries = [
    "What is the capital of France?",
    "Explain what AI is in simple terms",
    "Tell me a fun fact about space"
]

base_url = "http://localhost:8000"

# Wait for server
for i in range(5):
    try:
        requests.get(f"{base_url}/health", timeout=2)
        print("[OK] Server is ready")
        break
    except:
        if i < 4:
            print(f"Waiting for server... ({i+1}/5)")
            time.sleep(2)
        else:
            print("[FAIL] Server not running")
            print("Start server: python standalone_chat_fixed_ai.py")
            exit(1)

print("\n" + "="*60)
print("TEST RESULTS")
print("="*60)

for query in test_queries:
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": query, "user_id": "test_ai"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_used = data.get('ai_used', False)
            
            print(f"\nQ: {query}")
            print(f"A: {data['response'][:150]}...")
            
            if ai_used:
                print(f"✅ AI: REAL Cohere AI response")
            else:
                print(f"⚠️ AI: Fallback response (AI not working)")
        else:
            print(f"\n[FAIL] {query}: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n[ERROR] {query}: {e}")

print("\n" + "="*60)
