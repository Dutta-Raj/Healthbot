# comprehensive_test.py
"""Comprehensive test for the chat server"""

import requests
import json
import time

def test_server():
    print("\n" + "="*60)
    print("COMPREHENSIVE CHAT SERVER TEST")
    print("="*60)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    print("\n[TEST 1] Health Check")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Health endpoint working")
            print(f"  Response: {response.json()}")
        else:
            print(f"  [FAIL] Health check returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Cannot connect to server: {e}")
        print("\n  Make sure the server is running: python standalone_chat_fixed.py")
        return False
    
    # Test 2: Root endpoint
    print("\n[TEST 2] Root Endpoint")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("  [OK] Root endpoint working")
            data = response.json()
            print(f"  Message: {data.get('message', 'N/A')}")
        else:
            print(f"  [WARN] Root endpoint returned {response.status_code}")
    except Exception as e:
        print(f"  [WARN] Root endpoint error: {e}")
    
    # Test 3: Test endpoint
    print("\n[TEST 3] Test Endpoint")
    try:
        response = requests.get(f"{base_url}/test", timeout=5)
        if response.status_code == 200:
            print("  [OK] Test endpoint working")
        else:
            print(f"  [WARN] Test endpoint returned {response.status_code}")
    except:
        print("  [WARN] Test endpoint not available")
    
    # Test 4: Chat endpoint with various medical queries
    print("\n[TEST 4] Chat Endpoint Tests")
    print("-" * 40)
    
    test_queries = [
        "What is normal blood pressure?",
        "I have a bad headache",
        "Tell me about diabetes",
        "I have a fever of 101",
        "How to take medication properly?",
        "What exercises are good for health?"
    ]
    
    success_count = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\n  Query {i}: {query[:50]}...")
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={
                    "message": query,
                    "user_id": f"test_user_{i}",
                    "session_id": "test_session_001"
                },
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"    [OK] Status: {data['status']}")
                print(f"    Response: {data['response'][:100]}...")
                success_count += 1
            else:
                print(f"    [FAIL] HTTP {response.status_code}")
                print(f"    Error: {response.text[:100]}")
        except Exception as e:
            print(f"    [ERROR] {e}")
    
    # Test 5: Error handling
    print("\n[TEST 5] Error Handling")
    print("-" * 40)
    
    # Test with empty message
    print("\n  Test: Empty message")
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "", "user_id": "test"},
            timeout=5
        )
        if response.status_code == 422:
            print("    [OK] Empty message properly rejected (422)")
        else:
            print(f"    [WARN] Returned {response.status_code}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Test without user_id
    print("\n  Test: Missing user_id")
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Hello"},
            timeout=5
        )
        if response.status_code == 422:
            print("    [OK] Missing user_id properly rejected (422)")
        else:
            print(f"    [WARN] Returned {response.status_code}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Chat endpoint tests passed: {success_count}/{len(test_queries)}")
    
    if success_count == len(test_queries):
        print("\n[SUCCESS] All tests passed! The chat server is working perfectly.")
        return True
    else:
        print(f"\n[WARNING] {len(test_queries) - success_count} tests failed")
        return False

if __name__ == "__main__":
    test_server()
