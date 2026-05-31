import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DATABASE_NAME', 'healthbot_db')
    
    print(f"Connecting to MongoDB Atlas...")
    print(f"Database: {db_name}")
    
    # Connect with proper timeout
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    # Get or create database
    db = client[db_name]
    
    # Test write permission with a simple collection
    test_collection = db['_test_connection']
    test_result = test_collection.insert_one({"test": "success", "timestamp": "now"})
    test_collection.delete_one({"_id": test_result.inserted_id})
    
    print(f"\n✅ MongoDB Atlas Connected Successfully!")
    print(f"   Database: {db_name}")
    print(f"   Write Permission: GRANTED")
    print(f"   Read Permission: GRANTED")
    
    # Create required collections
    collections = ['users', 'conversations', 'sessions']
    for coll in collections:
        if coll not in db.list_collection_names():
            db.create_collection(coll)
            print(f"   Created collection: {coll}")
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    print("\nPlease ensure:")
    print("1. Network Access: Add IP 0.0.0.0/0 in MongoDB Atlas")
    print("2. Database User: Has 'readWriteAnyDatabase' role")
    sys.exit(1)
