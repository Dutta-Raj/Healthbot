# reset_user_password.py
"""Reset password for existing user"""

from pymongo import MongoClient
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

def reset_password():
    print("\n" + "="*50)
    print("PASSWORD RESET UTILITY")
    print("="*50)
    
    username = input("Enter username to reset password: ").strip()
    new_password = input("Enter new password: ").strip()
    
    if not username or not new_password:
        print("❌ Username and password required")
        return
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongo_uri)
    db = client[os.getenv('DATABASE_NAME', 'healthbot')]
    
    # Hash new password
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt)
    
    # Update user
    result = db.users.update_one(
        {"username": username},
        {"$set": {"password": hashed.decode('utf-8')}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Password reset successful for user: {username}")
        print(f"New password: {new_password}")
    else:
        print(f"❌ User not found: {username}")
        
        # List available users
        users = list(db.users.find({}, {"username": 1, "_id": 0}))
        if users:
            print("\nAvailable users:")
            for u in users:
                print(f"  - {u['username']}")

if __name__ == "__main__":
    reset_password()
