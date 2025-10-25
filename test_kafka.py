import requests
import json
import time

def register_user():
    """Register a test user if doesn't exist"""
    user_data = {
        "name": "Test User",
        "email": "test@example.com", 
        "password": "test123"
    }
    
    print("👤 Attempting to register test user...")
    try:
        response = requests.post("http://localhost:5000/register", json=user_data, timeout=10)
        if response.status_code == 201:
            print("✅ User registered successfully!")
            return response.json()["token"]
        else:
            print(f"ℹ️ Registration response: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return None

def login_user():
    """Login with test credentials"""
    login_data = {
        "email": "test@example.com",
        "password": "test123"
    }
    
    print("🔐 Attempting to login...")
    try:
        response = requests.post("http://localhost:5000/login", json=login_data, timeout=10)
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json()["token"]
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Error: {response.json().get('error', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def test_healthbot():
    print("🧪 Testing HealthBot with Kafka Alerts...")
    print("=" * 50)
    
    # First try to login
    token = login_user()
    
    # If login fails, try to register
    if not token:
        print("\n🔄 Login failed, trying to register new user...")
        token = register_user()
        
        # If registration successful, try login again
        if token:
            print("🔄 Registration successful, testing login...")
            token = login_user()
    
    if not token:
        print("\n❌ Could not authenticate. Please register a user manually at http://localhost:5000")
        return
    
    # Test messages
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}"
    }
    
    # Test 1: Normal message (no alert)
    print("\n1. Testing NORMAL message...")
    normal_data = {"message": "What foods are healthy for breakfast?"}
    
    try:
        response = requests.post("http://localhost:5000/chat", json=normal_data, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response received")
            print(f"   Alert triggered: {result.get('alert_triggered', 'Not specified')}")
            print(f"   Session ID: {result.get('session_id', 'Not specified')}")
        else:
            print(f"❌ Chat failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Critical message (should trigger alert)
    print("\n2. Testing CRITICAL alert message...")
    critical_data = {"message": "I have severe chest pain and can't breathe properly"}
    
    try:
        response = requests.post("http://localhost:5000/chat", json=critical_data, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response received")
            print(f"   🚨 Alert triggered: {result.get('alert_triggered', 'Not specified')}")
            print(f"   Session ID: {result.get('session_id', 'Not specified')}")
            if result.get('alert_triggered'):
                print("   ✅ ALERT SYSTEM WORKING - Check Flask console for '🚨 CRITICAL ALERT' message!")
        else:
            print(f"❌ Chat failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test completed! Check your Flask app terminal for alert messages.")

if __name__ == "__main__":
    # Wait a moment for server to be ready
    time.sleep(2)
    test_healthbot()
