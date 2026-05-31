# demo_healthbot.py
import requests
import json
import time

BASE = "http://localhost:8000"

print("🤖 HealthBot AI Complete Demo")
print("=" * 60)

# 1. System Status
print("\n📊 SYSTEM STATUS:")
status = requests.get(f"{BASE}/health").json()
for key, value in status.items():
    print(f"   {key}: {value}")

# 2. Send a medical question
print("\n💬 CHAT TEST:")
question = "What should I do if I have a fever?"
print(f"   Question: {question}")
response = requests.post(
    f"{BASE}/chat/stream",
    json={"message": question, "user_id": "demo_user"}
)
print(f"   Answer: {response.text[:200]}...")

# 3. Check queue statistics
print("\n📨 MESSAGE QUEUE STATS:")
stats = requests.get(f"{BASE}/queue/stats").json()
for topic, count in stats.items():
    print(f"   {topic}: {count} messages")

# 4. Get recent messages
print("\n📝 RECENT CHAT REQUESTS:")
try:
    requests_data = requests.get(f"{BASE}/queue/messages/requests").json()
    for msg in requests_data.get('messages', [])[-3:]:
        data = msg.get('data', {})
        print(f"   👤 {data.get('user_id')}: {data.get('message', '')[:50]}")
except:
    print("   No messages yet")

print("\n✅ Demo complete! Your HealthBot AI is fully functional!")
