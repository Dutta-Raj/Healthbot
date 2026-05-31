# final_test_all.py
"""Complete final test for Medical Chatbot System"""

import requests
import json
import time
import os
import sys
from datetime import datetime

print("\n" + "="*70)
print("🤖 MEDICAL CHATBOT - FINAL SYSTEM TEST")
print("="*70)

results = {"pass": 0, "fail": 0, "total": 0}

def test_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    if passed:
        results["pass"] += 1
    else:
        results["fail"] += 1
    results["total"] += 1
    print(f"{status}: {name}")
    if details:
        print(f"   📝 {details}")

# 1. Test Server Connection
print("\n" + "="*70)
print("📡 SERVER CONNECTION TESTS")
print("="*70)

base_url = "http://localhost:8000"

# Test Health Endpoint
try:
    response = requests.get(f"{base_url}/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        test_result("Health Endpoint", True, f"Status: {data.get('status')}, DB: {data.get('database')}")
    else:
        test_result("Health Endpoint", False, f"HTTP {response.status_code}")
except Exception as e:
    test_result("Health Endpoint", False, str(e))

# 2. Test Authentication
print("\n" + "="*70)
print("🔐 AUTHENTICATION TESTS")
print("="*70)

test_user = {
    "username": f"testuser_{int(time.time())}",
    "email": f"test_{int(time.time())}@test.com",
    "password": "Test123!",
    "full_name": "Test User"
}

# Test Registration
try:
    reg_response = requests.post(f"{base_url}/auth/register", json=test_user, timeout=5)
    if reg_response.status_code == 200:
        test_result("User Registration", True, f"User: {test_user['username']}")
        reg_data = reg_response.json()
        auth_token = reg_data.get('access_token')
    else:
        test_result("User Registration", False, f"HTTP {reg_response.status_code}")
        # Try login with demo account
        demo_login = {"username": "ab", "password": "ab123"}
        login_resp = requests.post(f"{base_url}/auth/login", json=demo_login, timeout=5)
        if login_resp.status_code == 200:
            auth_token = login_resp.json().get('access_token')
            test_result("Demo Login", True, "Using demo account: ab/ab123")
        else:
            auth_token = None
            test_result("Demo Login", False, "No working credentials")
except Exception as e:
    test_result("User Registration", False, str(e))
    auth_token = None

# Test Login
if auth_token:
    test_result("Auth Token Generated", True, f"Token length: {len(auth_token)}")
else:
    test_result("Auth Token Generated", False, "No token available")

# 3. Test Chat Functionality
print("\n" + "="*70)
print("💬 CHAT FUNCTIONALITY TESTS")
print("="*70)

if auth_token:
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    test_queries = [
        ("Medical Query - Blood Pressure", "What is normal blood pressure?"),
        ("Medical Query - Headache", "I have a headache, what should I do?"),
        ("Medical Query - Diabetes", "How to manage diabetes?"),
        ("Medical Query - Leg Pain", "What causes leg pain?"),
        ("Non-Medical Query", "What is the weather today?")
    ]
    
    for test_name, query in test_queries:
        try:
            chat_response = requests.post(
                f"{base_url}/chat",
                json={"message": query, "session_id": "final_test_session"},
                headers=headers,
                timeout=15
            )
            
            if chat_response.status_code == 200:
                data = chat_response.json()
                response_text = data.get('response', '')
                is_medical = "medical" in test_name.lower()
                
                if is_medical:
                    # Should get medical response
                    if len(response_text) > 50 and not ("non-medical" in response_text.lower() or "weather" in response_text.lower()):
                        test_result(test_name, True, f"Response length: {len(response_text)} chars")
                    else:
                        test_result(test_name, False, "Response too short or non-medical")
                else:
                    # Non-medical should be rejected
                    if "medical" in response_text.lower() or "health" in response_text.lower():
                        test_result(test_name, True, "Properly rejected non-medical query")
                    else:
                        test_result(test_name, False, "Should have rejected non-medical query")
            else:
                test_result(test_name, False, f"HTTP {chat_response.status_code}")
        except Exception as e:
            test_result(test_name, False, str(e))
else:
    print("⚠️ Skipping chat tests - no authentication token")

# 4. Test Conversation History
print("\n" + "="*70)
print("📜 CONVERSATION HISTORY TESTS")
print("="*70)

if auth_token:
    headers = {"Authorization": f"Bearer {auth_token}"}
    session_id = "final_test_session"
    
    try:
        history_response = requests.get(f"{base_url}/history/{session_id}", headers=headers, timeout=5)
        if history_response.status_code == 200:
            data = history_response.json()
            history_count = len(data.get('history', []))
            test_result("Conversation History", True, f"Found {history_count} messages in session")
        else:
            test_result("Conversation History", False, f"HTTP {history_response.status_code}")
    except Exception as e:
        test_result("Conversation History", False, str(e))

# 5. Test CORS Headers
print("\n" + "="*70)
print("🌐 CORS CONFIGURATION TEST")
print("="*70)

try:
    options_response = requests.options(f"{base_url}/chat", timeout=5)
    cors_header = options_response.headers.get('access-control-allow-origin', 'Not set')
    if cors_header == '*':
        test_result("CORS Headers", True, "Allow-Origin: *")
    else:
        test_result("CORS Headers", False, f"Allow-Origin: {cors_header}")
except Exception as e:
    test_result("CORS Headers", False, str(e))

# 6. Test Response Quality
print("\n" + "="*70)
print("🎯 RESPONSE QUALITY TESTS")
print("="*70)

if auth_token:
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    quality_checks = [
        ("Blood Pressure Info", "blood pressure", ["120/80", "mmHg", "normal"]),
        ("Headache Info", "headache", ["rest", "hydrate", "pain"]),
        ("Diabetes Info", "diabetes", ["blood sugar", "glucose", "management"]),
    ]
    
    for test_name, query, keywords in quality_checks:
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={"message": query, "session_id": "quality_test"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').lower()
                
                found_keywords = [kw for kw in keywords if kw in response_text]
                if len(found_keywords) >= 2:
                    test_result(test_name, True, f"Found keywords: {', '.join(found_keywords)}")
                else:
                    test_result(test_name, False, f"Missing keywords: {keywords}")
            else:
                test_result(test_name, False, f"HTTP {response.status_code}")
        except Exception as e:
            test_result(test_name, False, str(e))

# 7. System Summary
print("\n" + "="*70)
print("📊 FINAL SYSTEM SUMMARY")
print("="*70)

pass_percentage = (results["pass"] / results["total"] * 100) if results["total"] > 0 else 0

print(f"""
┌─────────────────────────────────────────────────────────────┐
│                    TEST RESULTS                             │
├─────────────────────────────────────────────────────────────┤
│  ✅ PASSED:  {results["pass"]}/{results["total"]}
│  ❌ FAILED:  {results["fail"]}/{results["total"]}
│  📈 RATE:    {pass_percentage:.1f}%
└─────────────────────────────────────────────────────────────┘
""")

if results["fail"] == 0:
    print("\n🎉 ALL TESTS PASSED! System is PRODUCTION READY!")
    print("\n✅ Ready for GitHub push and Render deployment!")
elif results["fail"] <= 2:
    print("\n⚠️ Minor issues detected. System may still work but review failures.")
else:
    print("\n❌ Multiple failures detected. Please fix before deployment.")

print("\n" + "="*70)
print("🏁 FINAL TEST COMPLETE")
print("="*70)
