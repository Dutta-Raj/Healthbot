# e2e_test.py
"""End-to-end test for the chatbot"""
import requests
import json
import time

def test_end_to_end():
    print("\nRunning end-to-end test...")
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("[OK] Health check passed")
        else:
            print("[FAIL] Health check failed")
            return False
    except:
        print("[FAIL] Cannot connect to backend")
        return False
    
    # Test chat functionality
    test_messages = [
        "What is my blood pressure?",
        "I have a headache",
        "Tell me about diabetes"
    ]
    
    for message in test_messages:
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={"message": message, "user_id": "e2e_test_user"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Chat response for '{message[:30]}...'")
            else:
                print(f"[WARN] Chat failed for: {message}")
        except Exception as e:
            print(f"[FAIL] Chat error: {e}")
    
    return True

if __name__ == "__main__":
    test_end_to_end()
