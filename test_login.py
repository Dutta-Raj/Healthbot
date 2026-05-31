import requests
import json

# Try to login with gg - you need to enter the correct password
print("\nTesting login for user 'gg'")
print("If you don't know the password, you can reset it or create a new user")

# Test with demo user 'ab' which we know works
login_data = {
    "username": "ab",
    "password": "ab123"
}

try:
    response = requests.post("http://localhost:8000/auth/login", json=login_data, timeout=5)
    if response.status_code == 200:
        print("✅ Demo user 'ab' logged in successfully")
        print(f"   Token received: {response.json()['access_token'][:50]}...")
    else:
        print(f"❌ Demo login failed: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
