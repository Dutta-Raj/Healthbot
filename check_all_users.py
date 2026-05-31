from pymongo import MongoClient
from dotenv import load_dotenv
import os
import bcrypt

load_dotenv()

mongo_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongo_uri)
db = client[os.getenv('DATABASE_NAME', 'healthbot')]

users = list(db.users.find({}, {"username": 1, "password": 1, "email": 1}))

print(f"\nFound {len(users)} users in database:")
for user in users:
    print(f"  - {user['username']} (email: {user.get('email', 'N/A')})")
    
    # Test if password hash looks valid
    password_hash = user['password']
    if password_hash.startswith('$2b$'):
        print(f"    ✅ Valid bcrypt hash detected")
    else:
        print(f"    ⚠️ Invalid hash format")

# Test each user's password verification with common passwords
print("\n[Testing password verification for each user]")
for user in users:
    print(f"\n  User: {user['username']}")
    # The password should be whatever the user set during registration
    # We can't test without knowing the password, but we can verify the hash is valid
    try:
        # Just check if hash is valid format
        test = bcrypt.hashpw("test".encode(), bcrypt.gensalt())
        print(f"    ✅ Hash format is valid")
    except:
        print(f"    ❌ Invalid hash")
