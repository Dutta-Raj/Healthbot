import os
import re

api_files = ['main_api.py', 'main_api_with_db.py', 'main_api_with_db_fixed.py', 'main_api_with_kafka.py']

print("\nSearching for /chat endpoint in API files:")
print("=" * 50)

for api_file in api_files:
    if os.path.exists(api_file):
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(r'@app\.(?:post|get)\(["\']/chat["\']', content):
                print(f"[FOUND] {api_file} has /chat endpoint")
                # Extract the endpoint definition
                match = re.search(r'(@app\.(?:post|get)\(["\']/chat["\']\)[\s\S]+?def\s+(\w+)[\s\S]+?return[\s\S]+?)(?=\n@|\Z)', content)
                if match:
                    print(f"  Endpoint: {match.group(2)}")
            else:
                print(f"[NO] {api_file} does not have /chat endpoint")
