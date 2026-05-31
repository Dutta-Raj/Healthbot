# test_working.py
import requests
import time

print("\n" + "="*60)
print("TESTING WORKING AI CHATBOT")
print("="*60)

base = "http://localhost:8000"

# Wait for server
for i in range(5):
    try:
        r = requests.get(f"{base}/health", timeout=2)
        if r.status_code == 200:
            print("[OK] Server ready")
            print(f"  Models: {r.json().get('models_available', ['unknown'])[0]}")
            break
    except:
        time.sleep(2)

# Test queries
tests = [
    "What is normal blood pressure?",
    "Tell me a short joke",
    "I have a headache",
]

for q in tests:
    print(f"\nQ: {q}")
    try:
        r = requests.post(f"{base}/chat", json={"message": q, "user_id": "test"})
        if r.status_code == 200:
            data = r.json()
            print(f"A: {data['response'][:150]}...")
            print(f"🤖 AI Model: {data.get('ai_model', 'unknown')}")
            print(f"✅ AI Used: {data.get('ai_used', False)}")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*60)
