# direct_cohere_test.py
"""Direct test of Cohere API"""

import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("DIRECT COHERE API TEST")
print("="*60)

# Get API key
api_key = os.getenv('COHERE_API_KEY')
if not api_key:
    print("[FAIL] No COHERE_API_KEY found in .env file")
    exit(1)
else:
    print(f"[OK] API Key found: {api_key[:10]}...{api_key[-5:]}")
    print(f"    Key length: {len(api_key)} characters")

# Test Cohere connection
try:
    import cohere
    print(f"[OK] Cohere package imported")
    
    # Try different models
    models_to_try = [
        "command",
        "command-light", 
        "command-nightly",
        "command-r",
        "command-r-plus"
    ]
    
    print("\n[TEST] Trying different models...")
    
    for model in models_to_try:
        try:
            print(f"\n  Testing model: {model}")
            co = cohere.Client(api_key=api_key)
            
            response = co.chat(
                message="Say 'Hello' in one word",
                model=model,
                max_tokens=10,
                temperature=0.5
            )
            
            if response and response.text:
                print(f"    [OK] Model '{model}' works!")
                print(f"    Response: {response.text}")
                print(f"\n[SUCCESS] Use model: {model}")
                break
            else:
                print(f"    [FAIL] No response from {model}")
                
        except Exception as e:
            error_msg = str(e)
            if "deprecated" in error_msg.lower():
                print(f"    [DEPRECATED] {model} is deprecated")
            elif "invalid model" in error_msg.lower():
                print(f"    [INVALID] {model} not available")
            else:
                print(f"    [ERROR] {model}: {error_msg[:100]}")
    
    # If none worked, try to list available models
    print("\n[INFO] Trying to list available models...")
    try:
        co = cohere.Client(api_key=api_key)
        # This might not work in all versions
        print("  Use 'command' or 'command-light' as safe defaults")
    except:
        pass
        
except ImportError as e:
    print(f"[FAIL] Cohere package not installed: {e}")
    print("Install with: pip install cohere")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)
print("Based on the test results, update your server to use the working model")
print("="*60)
