import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    print(f"Connecting to MongoDB Atlas...")
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    db_name = os.getenv('DATABASE_NAME', 'healthbot_db')
    db = client[db_name]
    
    # Create collections
    collections = ['users', 'conversations', 'sessions', 'feedback']
    for coll in collections:
        if coll not in db.list_collection_names():
            db.create_collection(coll)
            print(f"  Created collection: {coll}")
    
    # Create indexes
    db.users.create_index("username", unique=True)
    db.users.create_index("email", unique=True)
    db.conversations.create_index("user_id")
    db.conversations.create_index("timestamp")
    
    print(f"\n✅ MongoDB Atlas Connected Successfully!")
    print(f"   Database: {db_name}")
    print(f"   Collections: {', '.join(db.list_collection_names())}")
    
    sys.exit(0)
except Exception as e:
    print(f"❌ MongoDB Atlas connection failed: {e}")
    sys.exit(1)
