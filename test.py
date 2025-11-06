# test.py
import openai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"Testing API Key: {api_key[:25]}...")

client = openai.OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'Hello'"}],
        max_tokens=5
    )
    print("✅ SUCCESS! Response:", response.choices[0].message.content)
except Exception as e:
    print(f"❌ FAILED: {e}")