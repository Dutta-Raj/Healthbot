import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Test connection
mongo_uri = f"mongodb+srv://{os.getenv('MONGO_USERNAME')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_CLUSTER')}/{os.getenv('MONGO_DB_NAME')}?retryWrites=true&w=majority"

print("Testing MongoDB connection...")
print(f"URI: mongodb+srv://{os.getenv('MONGO_USERNAME')}:******@{os.getenv('MONGO_CLUSTER')}/{os.getenv('MONGO_DB_NAME')}")

try:
    client = MongoClient(mongo_uri)
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful!")
    
    # List databases
    print("Available databases:")
    for db_name in client.list_database_names():
        print(f" - {db_name}")
        
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")