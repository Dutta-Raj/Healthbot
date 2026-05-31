import requests
import json

try:
    response = requests.get("http://localhost:8000/openapi.json", timeout=5)
    if response.status_code == 200:
        print("\nAvailable endpoints:")
        print("=" * 50)
        paths = response.json().get('paths', {})
        for path, methods in sorted(paths.items()):
            print(f"{path}: {', '.join(methods.keys())}")
    else:
        print(f"Cannot fetch API docs: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
