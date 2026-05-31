import requests
import json
import sys

print("\nDetailed Chat Endpoint Test")
print("=" * 50)

base_url = "http://localhost:8000"

# Test 1: Check if chat endpoint exists
try:
    response = requests.options(f"{base_url}/chat", timeout=5)
    print(f"[INFO] OPTIONS request: {response.status_code}")
except:
    pass

# Test 2: Try different payload formats
test_payloads = [
    {"message": "Hello", "user_id": "test_user"},
    {"query": "What is my blood pressure?", "user_id": "test_user"},
    {"text": "I have a headache", "user_id": "test_user"},
    {"message": "Hello", "user_id": "test_user", "session_id": "test_session"}
]

for i, payload in enumerate(test_payloads, 1):
    try:
        print(f"\nTest {i}: Payload = {payload}")
        response = requests.post(
            f"{base_url}/chat",
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            break
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")

# Test 3: Check if there's an alternative endpoint
alternative_endpoints = ["/query", "/ask", "/converse", "/api/chat"]
for endpoint in alternative_endpoints:
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            json={"message": "Hello", "user_id": "test"},
            timeout=5
        )
        if response.status_code != 404:
            print(f"\n[FOUND] Alternative endpoint: {endpoint}")
            print(f"  Response: {response.status_code}")
    except:
        pass

# Test 4: Check API documentation
try:
    response = requests.get(f"{base_url}/openapi.json", timeout=5)
    if response.status_code == 200:
        api_docs = response.json()
        print("\n[INFO] Available endpoints:")
        for path, methods in api_docs.get('paths', {}).items():
            print(f"  {path}: {list(methods.keys())}")
except Exception as e:
    print(f"\n[ERROR] Cannot fetch API docs: {e}")
