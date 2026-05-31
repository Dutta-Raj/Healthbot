import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

mongo_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongo_uri)
db = client[os.getenv('DATABASE_NAME', 'healthbot')]

user = db.users.find_one({"username": "gg"})

if user:
    print(f"\nUser found: {user['username']}")
    print(f"Stored hash: {user['password'][:50]}...")
    
    # Test different passwords
    test_passwords = ["gg", "gg123", "gg@123", "password", "gggg"]
    
    print("\nTesting possible passwords:")
    for pwd in test_passwords:
        try:
            if bcrypt.checkpw(pwd.encode('utf-8'), user['password'].encode('utf-8')):
                print(f"  ✅ CORRECT PASSWORD: '{pwd}'")
                break
        except:
            pass
    
    # Reset password to a known value
    print("\n[Resetting password for 'gg' to 'gg123']")
    new_hash = bcrypt.hashpw("gg123".encode('utf-8'), bcrypt.gensalt())
    db.users.update_one({"username": "gg"}, {"$set": {"password": new_hash.decode('utf-8')}})
    print("  ✅ Password reset to 'gg123'")
else:
    print("User 'gg' not found")
