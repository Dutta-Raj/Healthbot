# run_server.py
"""Simple script to run the chat server"""
import subprocess
import sys
import time

print("Starting Chat Server...")
print("=" * 50)

# Run the server
try:
    subprocess.run([sys.executable, "standalone_chat_fixed.py"])
except KeyboardInterrupt:
    print("\nServer stopped by user")
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying to run with uvicorn directly...")
    subprocess.run([sys.executable, "-m", "uvicorn", "standalone_chat_fixed:app", "--host", "0.0.0.0", "--port", "8000"])
