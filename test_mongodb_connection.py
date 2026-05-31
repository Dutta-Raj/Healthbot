# test_mongodb_connection.py
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def test_connection():
    username = os.getenv("MONGO_USERNAME", "Rajdeep2004")
    password = os.getenv("MONGO_PASSWORD", "Rajdeep-2004")
    cluster = os.getenv("MONGO_CLUSTER", "cluster0.qs43zoc.mongodb.net")
    
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority"
    
    try:
        client = AsyncIOMotorClient(connection_string)
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB!")
        
        # List databases
        databases = await client.list_database_names()
        print(f"📚 Available databases: {databases}")
        
        client.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
