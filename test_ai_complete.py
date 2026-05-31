# test_ai_complete.py
"""Test if Cohere AI is working properly"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("AI FUNCTIONALITY DIAGNOSTIC")
print("="*60)

# Check 1: Environment variable
print("\n[1] Checking Cohere API Key...")
cohere_key = os.getenv('COHERE_API_KEY')
if cohere_key:
    print(f"  [OK] API Key found: {cohere_key[:10]}...{cohere_key[-5:]}")
else:
    print("  [FAIL] No COHERE_API_KEY found in .env file")
    print("  AI will use fallback responses only")

# Check 2: Cohere package
print("\n[2] Checking Cohere package...")
try:
    import cohere
    print(f"  [OK] Cohere package version: {cohere.__version__ if hasattr(cohere, '__version__') else 'installed'}")
except ImportError:
    print("  [FAIL] Cohere package not installed")
    print("  Install with: pip install cohere")

# Check 3: Direct Cohere API test
if cohere_key:
    print("\n[3] Testing Cohere API connection...")
    try:
        import cohere
        
        # Try new ClientV2
        try:
            co = cohere.ClientV2(api_key=cohere_key)
            response = co.chat(
                model="command-r-plus",
                messages=[{"role": "user", "content": "Say 'AI is working'"}],
                max_tokens=20
            )
            if response and response.message:
                print("  [OK] Cohere Chat API (V2) is WORKING!")
                print(f"  Response: {response.message.content[0].text}")
                ai_working = True
        except Exception as e1:
            # Try legacy client
            try:
                co = cohere.Client(api_key=cohere_key)
                response = co.chat(
                    message="Say 'AI is working'",
                    model="command-r-plus",
                    max_tokens=20
                )
                if response and hasattr(response, 'text'):
                    print("  [OK] Cohere Chat API (Legacy) is WORKING!")
                    print(f"  Response: {response.text}")
                    ai_working = True
            except Exception as e2:
                print(f"  [FAIL] Cohere API error: {e2}")
                ai_working = False
    except Exception as e:
        print(f"  [FAIL] Cohere import error: {e}")
        ai_working = False
else:
    ai_working = False

# Check 4: Test actual chat endpoint
print("\n[4] Testing /chat endpoint with AI...")
test_queries = [
    "What is the capital of France?",  # Non-medical to test AI
    "Explain quantum physics simply",   # Complex topic
    "Tell me a joke about doctors"      # Creative response
]

for query in test_queries:
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"message": query, "user_id": "ai_test"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            answer = data['response']
            
            # Check if response seems AI-generated or fallback
            if "I understand you're asking about" in answer or "health assistant" in answer:
                print(f"  [WARN] Query: '{query[:30]}...' -> Using FALLBACK response")
                print(f"    Response: {answer[:80]}...")
            else:
                print(f"  [OK] Query: '{query[:30]}...' -> Using AI response")
                print(f"    Response: {answer[:80]}...")
        else:
            print(f"  [FAIL] Chat endpoint error: {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] {e}")

# Check 5: Compare AI vs Fallback
print("\n[5] AI Status Summary:")
print("="*60)
if ai_working:
    print("  ✅ COHERE AI IS WORKING!")
    print("  The chatbot is using real AI responses")
else:
    print("  ⚠️ COHERE AI IS NOT WORKING")
    print("  The chatbot is using FALLBACK responses only")
    print("\n  To enable AI:")
    print("  1. Get a Cohere API key from https://dashboard.cohere.com")
    print("  2. Add it to .env file: COHERE_API_KEY=your_key_here")
    print("  3. Install cohere: pip install cohere")
    print("  4. Restart the server")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
