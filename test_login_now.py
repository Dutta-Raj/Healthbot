import requests
import json

print("\n" + "="*60)
print("TESTING LOGIN WITH UPDATED PASSWORD")
print("="*60)

# Test login
login_data = {
    "username": "ab",
    "password": "ab123"
}

try:
    response = requests.post(
        "http://localhost:8000/auth/login",
        json=login_data,
        timeout=5
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ LOGIN SUCCESSFUL!")
        print(f"   Username: {data.get('username')}")
        print(f"   Token: {data.get('access_token')[:60]}...")
    else:
        print("❌ Login failed")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
