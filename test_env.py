import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test if .env is loading
print("🔍 Checking .env file loading:")
print(f"OPENAI_API_KEY exists: {'OPENAI_API_KEY' in os.environ}")
print(f"MONGO_USERNAME exists: {'MONGO_USERNAME' in os.environ}")

if 'OPENAI_API_KEY' in os.environ:
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"API Key length: {len(api_key)}")
    print(f"API Key starts with: {api_key[:10]}...")
    print(f"API Key ends with: ...{api_key[-10:]}")
else:
    print("❌ OPENAI_API_KEY not found in environment")