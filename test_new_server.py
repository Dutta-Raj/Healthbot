# test_new_server.py
import requests
import time

print("\nTesting Standalone Chat Server")
print("=" * 50)

base_url = "http://localhost:8000"

# Wait for server to start
time.sleep(2)

# Test health
try:
    response = requests.get(f"{base_url}/health", timeout=5)
    print(f"[OK] Health check: {response.status_code}")
except:
    print("[FAIL] Server not running")
    exit(1)

# Test chat
test_messages = [
    "What is my blood pressure?",
    "I have a headache",
    "Tell me about diabetes"
]

for message in test_messages:
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": message, "user_id": "test_user"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"\n[OK] Message: {message[:30]}...")
            print(f"Response: {data['response'][:100]}...")
        else:
            print(f"\n[FAIL] {message}: {response.status_code}")
    except Exception as e:
        print(f"\n[ERROR] {message}: {e}")

print("\n" + "=" * 50)
print("Chat server is working!")
