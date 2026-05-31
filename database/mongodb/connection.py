# database/mongodb/connection.py
"""
MongoDB Connection Manager with Async Support
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT, GEO2D
from pymongo.write_concern import WriteConcern
from pymongo.read_preferences import ReadPreference
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class MongoDBConnection:
    """Singleton MongoDB Connection Manager"""
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish MongoDB connection"""
        if self._client is None:
            username = os.getenv("MONGO_USERNAME", "Rajdeep2004")
            password = os.getenv("MONGO_PASSWORD", "Rajdeep-2004")
            cluster = os.getenv("MONGO_CLUSTER", "cluster0.qs43zoc.mongodb.net")
            db_name = os.getenv("MONGO_DB_NAME", "myappdb")
            
            # Build connection string
            connection_string = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority"
            
            self._client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            await self._client.admin.command('ping')
            self._db = self._client[db_name]
            logger.info(f"Connected to MongoDB database: {db_name}")
        
        return self._db
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")
    
    async def get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._db is None:
            await self.connect()
        return self._db

# Global connection instance
mongodb = MongoDBConnection()
