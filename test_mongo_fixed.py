import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('DATABASE_NAME', 'myappdb')  # Use your existing database
    
    print(f"Connecting to MongoDB Atlas...")
    print(f"Database: {db_name}")
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
    
    # Use the database that exists
    db = client[db_name]
    
    # Try to list collections (may fail if no permissions)
    try:
        collections = db.list_collection_names()
        print(f"Collections found: {collections}")
    except Exception as e:
        print(f"Note: Limited permissions - {e}")
    
    # Try to create/access collections with proper permissions
    test_collection = db['test_connection']
    test_doc = {"test": "connection", "timestamp": "test"}
    test_collection.insert_one(test_doc)
    test_collection.delete_one({"test": "connection"})
    
    print(f"\n✅ MongoDB Atlas Connected Successfully!")
    print(f"   Database: {db_name}")
    print(f"   Write/Read permissions: WORKING")
    
    sys.exit(0)
except Exception as e:
    print(f"❌ MongoDB Atlas connection failed: {e}")
    print(f"\nTroubleshooting:")
    print(f"1. Go to MongoDB Atlas: https://cloud.mongodb.com")
    print(f"2. Click 'Network Access' -> Add IP Address 0.0.0.0/0")
    print(f"3. Click 'Database Access' -> Edit user -> Add 'readWriteAnyDatabase' role")
    sys.exit(1)
