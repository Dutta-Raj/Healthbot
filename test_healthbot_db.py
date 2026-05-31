import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DATABASE_NAME', 'healthbot')
    
    print(f"Connecting to MongoDB Atlas...")
    print(f"Database: {db_name}")
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    db = client[db_name]
    
    # List existing collections
    collections = db.list_collection_names()
    print(f"\n✅ Connected to '{db_name}' database!")
    print(f"   Existing collections: {collections if collections else 'none yet'}")
    
    # Create required collections if they don't exist
    required_collections = ['users', 'conversations', 'sessions', 'feedback']
    for coll in required_collections:
        if coll not in collections:
            db.create_collection(coll)
            print(f"   Created collection: {coll}")
    
    # Create indexes
    db.users.create_index("username", unique=True)
    db.users.create_index("email", unique=True)
    db.conversations.create_index("user_id")
    db.conversations.create_index("timestamp")
    
    print(f"\n✅ Database setup complete!")
    print(f"   Collections ready: {', '.join(required_collections)}")
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Connection error: {e}")
    print("\nMake sure:")
    print("1. Network Access has 0.0.0.0/0")
    print("2. User has readWrite permissions")
    sys.exit(1)
