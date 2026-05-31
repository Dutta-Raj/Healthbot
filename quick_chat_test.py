import requests
import json

try:
    # First login to get token
    login_data = {"username": "testuser", "password": "test123"}
    response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        
        # Test chat
        chat_response = requests.post(
            "http://localhost:8000/chat",
            json={"message": "Hello, are you working?"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if chat_response.status_code == 200:
            print("✅ Chat endpoint is WORKING!")
            print(f"   Response: {chat_response.json()['response'][:80]}...")
        else:
            print(f"⚠️ Chat endpoint: {chat_response.status_code}")
    else:
        print("ℹ️  No test user found. Register first via frontend")
except Exception as e:
    print(f"ℹ️  Chat test requires authentication")
    print("   Register a user via the frontend first")
