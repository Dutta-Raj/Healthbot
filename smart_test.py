# smart_test.py
"""Test that waits for server to be ready"""
import requests
import time
import sys

def wait_for_server(max_attempts=10, delay=2):
    """Wait for server to be ready"""
    print("Waiting for server to start...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Server is ready! (attempt {attempt + 1})")
                return True
        except:
            print(f"  Attempt {attempt + 1}/{max_attempts} - Server not ready yet...")
            time.sleep(delay)
    
    print("[FAIL] Server did not start within expected time")
    return False

def test_chat():
    """Test chat endpoint"""
    print("\n" + "="*50)
    print("TESTING CHAT ENDPOINT")
    print("="*50)
    
    test_messages = [
        "What is my blood pressure?",
        "I have a headache",
        "Tell me about diabetes"
    ]
    
    for msg in test_messages:
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": msg, "user_id": "test_user"},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                print(f"\n[OK] Message: {msg[:40]}...")
                print(f"Response: {data['response'][:100]}...")
            else:
                print(f"\n[FAIL] {msg}: {response.status_code}")
        except Exception as e:
            print(f"\n[ERROR] {msg}: {e}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    if wait_for_server():
        test_chat()
    else:
        print("\nPlease start the server first:")
        print("  python standalone_chat_fixed.py")
        sys.exit(1)
