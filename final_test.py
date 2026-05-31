# final_test.py
"""Test the fully working AI chatbot"""

import requests
import time

print("\n" + "="*60)
print("HEALTHBOT AI - FINAL TEST")
print("="*60)

base_url = "http://localhost:8000"

# Wait for server
print("Waiting for server...")
for i in range(5):
    try:
        r = requests.get(f"{base_url}/health", timeout=2)
        if r.status_code == 200:
            print("[OK] Server ready!")
            break
    except:
        time.sleep(2)
else:
    print("[FAIL] Server not running")
    exit(1)

# Get server info
try:
    info = requests.get(f"{base_url}/info").json()
    print(f"\n[INFO] AI Status: {info['ai_status']}")
    print(f"[INFO] Model: {info['ai_model']}")
except:
    pass

# Test queries
print("\n" + "="*60)
print("TESTING AI RESPONSES")
print("="*60)

test_cases = [
    ("General", "What is artificial intelligence?"),
    ("Medical", "What causes high blood pressure?"),
    ("Creative", "Tell me a short joke"),
    ("Health", "How can I prevent diabetes?")
]

for category, query in test_cases:
    print(f"\n[{category}] Q: {query}")
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": query, "user_id": "test_user"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"A: {data['response'][:150]}...")
            
            if data.get('ai_used'):
                print(f"✅ [REAL AI] Used model: {data.get('model', 'unknown')}")
            else:
                print(f"⚠️ [FALLBACK] AI not used")
        else:
            print(f"❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*60)
print("✅ TEST COMPLETE")
print("="*60)
print("\nThe chatbot uses:")
print("• Cohere command-nightly for AI responses")
print("• Medical database for fallback")
print("• Real AI for general questions")
print("="*60)
