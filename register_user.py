import requests
import json

def register_test_user():
    print("👤 Registering test user...")
    
    user_data = {
        "name": "Test User",
        "email": "test@example.com", 
        "password": "test123"
    }
    
    try:
        response = requests.post("http://localhost:5000/register", json=user_data, timeout=10)
        
        if response.status_code == 201:
            print("✅ User registered successfully!")
            token = response.json()["token"]
            print(f"Token: {token[:20]}...")
            return token
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Error: {response.json().get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure your Flask app is running on http://localhost:5000")
        return None

if __name__ == "__main__":
    register_test_user()