import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = pymongo.MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
    client.admin.command('ping')
    print("MongoDB is running!")
    
    # Create database and collections
    db = client[os.getenv('DATABASE_NAME', 'healthbot_db')]
    
    # Create collections if they don't exist
    collections = ['users', 'conversations', 'sessions', 'feedback']
    for coll in collections:
        if coll not in db.list_collection_names():
            db.create_collection(coll)
            print(f"Created collection: {coll}")
    
    # Create indexes for better performance
    db.users.create_index("username", unique=True)
    db.users.create_index("email", unique=True)
    db.conversations.create_index("user_id")
    db.conversations.create_index("timestamp")
    db.sessions.create_index("session_id", unique=True)
    db.sessions.create_index("user_id")
    
    print("Database indexes created!")
    print("MongoDB setup complete!")
    
except Exception as e:
    print(f"MongoDB not running: {e}")
    print("Install MongoDB from: https://www.mongodb.com/try/download/community")
