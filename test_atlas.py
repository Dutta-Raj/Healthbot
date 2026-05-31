# test_atlas.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Your Atlas connection details
username = os.getenv('MONGO_USERNAME', 'Rajdeep2004')
password = os.getenv('MONGO_PASSWORD', 'Rajdeep-2004')
cluster = os.getenv('MONGO_CLUSTER', 'cluster0.qs43zoc.mongodb.net')
db_name = os.getenv('MONGO_DB_NAME', 'myappdb')

# Create connection string
connection_string = f'mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority'

try:
    # Connect to Atlas
    client = MongoClient(connection_string)
    db = client[db_name]
    
    # Test connection
    client.admin.command('ping')
    print('✅ Successfully connected to MongoDB Atlas!')
    print(f'📊 Database: {db_name}')
    
    # List existing collections
    collections = db.list_collection_names()
    if collections:
        print(f'📚 Existing collections: {", ".join(collections)}')
    else:
        print('📚 No collections found yet')
    
    # Get database stats
    stats = db.command('dbStats')
    print(f'📈 Database size: {stats["dataSize"] / 1024 / 1024:.2f} MB')
    
    client.close()
    
except Exception as e:
    print(f'❌ Connection failed: {e}')
    print('💡 Troubleshooting tips:')
    print('   1. Check your username and password in .env file')
    print('   2. Add your IP address to MongoDB Atlas whitelist')
    print('   3. Make sure cluster name is correct')
