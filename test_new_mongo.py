import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DATABASE_NAME', 'healthbot_db')
    
    print(f"Connecting to MongoDB Atlas...")
    print(f"User: Rajnew2004")
    print(f"Database: {db_name}")
    
    # Connect
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    # Get database
    db = client[db_name]
    
    # Test write permission
    test_col = db['_test']
    result = test_col.insert_one({"test": "connection", "time": "now"})
    test_col.delete_one({"_id": result.inserted_id})
    
    # Create collections
    collections = ['users', 'conversations', 'sessions']
    for coll in collections:
        if coll not in db.list_collection_names():
            db.create_collection(coll)
            print(f"  Created collection: {coll}")
    
    print(f"\n✅ MongoDB Atlas Connected Successfully!")
    print(f"   Database: {db_name}")
    print(f"   Collections: {', '.join(db.list_collection_names())}")
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    sys.exit(1)
