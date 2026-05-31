import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DATABASE_NAME', 'healthbot')
    
    print(f"Connecting to MongoDB Atlas...")
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    db = client[db_name]
    
    print(f"✅ Connected to database: {db_name}")
    
    # Drop problematic indexes first
    print("\n[1] Cleaning up existing indexes...")
    try:
        db.users.drop_indexes()
        print("  Dropped existing indexes on users collection")
    except:
        pass
    
    # Create collections properly
    print("\n[2] Creating collections...")
    collections_needed = ['users', 'conversations', 'sessions', 'feedback']
    
    for coll_name in collections_needed:
        if coll_name not in db.list_collection_names():
            db.create_collection(coll_name)
            print(f"  Created collection: {coll_name}")
        else:
            print(f"  Collection exists: {coll_name}")
    
    # Create indexes properly
    print("\n[3] Creating indexes...")
    
    # Users collection indexes
    db.users.create_index("username", unique=True, sparse=True)
    print("  Created index: username (unique)")
    db.users.create_index("email", unique=True, sparse=True)
    print("  Created index: email (unique)")
    db.users.create_index("created_at")
    print("  Created index: created_at")
    
    # Conversations collection indexes
    db.conversations.create_index("user_id")
    print("  Created index: user_id")
    db.conversations.create_index("timestamp")
    print("  Created index: timestamp")
    db.conversations.create_index([("user_id", 1), ("timestamp", -1)])
    print("  Created index: user_id + timestamp")
    
    # Sessions collection indexes
    db.sessions.create_index("session_id", unique=True)
    print("  Created index: session_id (unique)")
    db.sessions.create_index("user_id")
    print("  Created index: user_id")
    db.sessions.create_index("created_at")
    print("  Created index: created_at")
    
    # Feedback collection indexes
    db.feedback.create_index("user_id")
    print("  Created index: user_id")
    db.feedback.create_index("timestamp")
    print("  Created index: timestamp")
    
    print("\n✅ MongoDB Atlas setup complete!")
    print(f"   Database: {db_name}")
    print(f"   Collections: {db.list_collection_names()}")
    
    # Test insert
    print("\n[4] Testing write permissions...")
    test_user = {
        "username": "test_temp",
        "email": "temp@test.com",
        "password": "temp",
        "created_at": "test"
    }
    try:
        db.users.insert_one(test_user)
        db.users.delete_one({"username": "test_temp"})
        print("  ✅ Write permission confirmed")
    except Exception as e:
        print(f"  ⚠️ Write test: {e}")
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting steps:")
    print("1. Go to MongoDB Atlas: https://cloud.mongodb.com")
    print("2. Click 'Network Access' → Add IP Address → 0.0.0.0/0")
    print("3. Click 'Database Access' → Edit user → Add 'readWriteAnyDatabase'")
    sys.exit(1)
