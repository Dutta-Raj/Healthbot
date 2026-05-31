# force_password_update.py
"""Force update password in database"""

from pymongo import MongoClient
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

print("\n" + "="*60)
print("FORCE PASSWORD UPDATE")
print("="*60)

# Connect to MongoDB
mongo_uri = os.getenv('MONGODB_URI')
print(f"Connecting to MongoDB Atlas...")

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = client[os.getenv('DATABASE_NAME', 'healthbot')]

# First, let's see all users
print("\n[1] Current users in database:")
all_users = list(db.users.find({}, {"username": 1, "_id": 1}))
for u in all_users:
    print(f"  - {u['username']} (ID: {u['_id']})")

# Find user 'ab'
user = db.users.find_one({"username": "ab"})

if not user:
    print("\n❌ User 'ab' not found!")
    
    # Create user if not exists
    print("\nCreating user 'ab'...")
    new_password = "ab123"
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt)
    
    new_user = {
        "username": "ab",
        "email": "ab@healthbot.com",
        "password": hashed.decode('utf-8'),
        "full_name": "AB User",
        "created_at": datetime.now(),
        "role": "user"
    }
    result = db.users.insert_one(new_user)
    print(f"✅ User created with ID: {result.inserted_id}")
    print(f"   Password: {new_password}")
else:
    print(f"\n[2] Found user: {user['username']}")
    print(f"    Current hash: {user['password'][:40]}...")
    
    # Set new password
    new_password = "ab123"
    print(f"\n[3] Setting new password to: {new_password}")
    
    # Generate new hash
    salt = bcrypt.gensalt(rounds=12)
    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt)
    new_hash_str = new_hash.decode('utf-8')
    
    # Update the user
    result = db.users.update_one(
        {"username": "ab"},
        {"$set": {"password": new_hash_str}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Password updated successfully!")
        print(f"   New hash: {new_hash_str[:40]}...")
        
        # Verify the new password
        print(f"\n[4] Verifying new password...")
        verify_result = bcrypt.checkpw(new_password.encode('utf-8'), new_hash)
        print(f"   Verification: {'✅ SUCCESS' if verify_result else '❌ FAILED'}")
    else:
        print(f"❌ Failed to update (modified_count: {result.modified_count})")

# Also delete any problematic indexes
print(f"\n[5] Checking indexes...")
try:
    db.users.drop_index("username_1")
    print("   Dropped username index")
except:
    pass

# Create fresh index
db.users.create_index("username", unique=True)
print("   Created fresh username index")

print(f"\n" + "="*60)
print("✅ Password update complete!")
print(f"   Username: ab")
print(f"   Password: ab123")
print("="*60)

client.close()
