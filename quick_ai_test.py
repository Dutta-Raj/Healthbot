# quick_ai_test.py
import requests
import time

print("\n" + "="*60)
print("TESTING COHERE AI CHATBOT")
print("="*60)

base_url = "http://localhost:8000"

# Test if server is ready
for i in range(5):
    try:
        r = requests.get(f"{base_url}/health", timeout=2)
        if r.status_code == 200:
            print("[OK] Server is ready!")
            break
    except:
        if i < 4:
            print(f"Waiting for server... ({i+1}/5)")
            time.sleep(2)
        else:
            print("[FAIL] Server not responding")
            exit(1)

# Test with different query types
test_queries = [
    ("General Knowledge", "What is the capital of Japan?"),
    ("Creative", "Tell me a short joke about programmers"),
    ("Medical", "What are symptoms of common cold?")
]

print("\n" + "="*60)
print("AI RESPONSE TEST")
print("="*60)

for test_type, query in test_queries:
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": query, "user_id": "test_user"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_used = data.get('ai_used', False)
            
            print(f"\n[{test_type}] Query: {query}")
            print(f"Response: {data['response'][:150]}...")
            
            if ai_used:
                print("✅ STATUS: REAL Cohere AI response")
            else:
                print("⚠️ STATUS: Fallback response")
        else:
            print(f"\n[FAIL] {test_type}: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n[ERROR] {test_type}: {e}")

print("\n" + "="*60)
print("Test Complete!")
print("="*60)
