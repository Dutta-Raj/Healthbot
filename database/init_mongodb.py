# database/init_mongodb.py
"""
Initialize MongoDB with all indexes and sample data
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb.connection import mongodb
from database.mongodb.schema import mongo_schema
from database.repositories.base_repository import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    MedicalKnowledgeRepository
)
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_database():
    """Initialize complete database setup"""
    try:
        logger.info("🚀 Starting MongoDB initialization...")
        
        # Test connection
        db = await mongodb.connect()
        logger.info("✅ Connected to MongoDB")
        
        # Create all collections and indexes
        await mongo_schema.initialize_collections()
        logger.info("✅ All indexes created successfully")
        
        # Test repositories
        user_repo = UserRepository()
        
        # Create test user if needed
        test_user = await user_repo.find_by_email("test@healthbot.com")
        if not test_user:
            test_user_id = await user_repo.create({
                "email": "test@healthbot.com",
                "full_name": "Test User",
                "is_active": True,
                "is_verified": True
            })
            logger.info(f"✅ Created test user: {test_user_id}")
        
        # Get database stats
        stats = await db.command("dbStats")
        logger.info(f"📊 Database Stats: {stats['dataSize'] / 1024 / 1024:.2f} MB")
        
        # List all collections
        collections = await db.list_collection_names()
        logger.info(f"📚 Collections: {', '.join(collections)}")
        
        logger.info("🎉 Database initialization complete!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await mongodb.disconnect()

async def get_database_stats():
    """Get detailed database statistics"""
    db = await mongodb.get_db()
    
    stats = {}
    collections = await db.list_collection_names()
    
    for collection_name in collections:
        collection = db[collection_name]
        stats[collection_name] = {
            "count": await collection.count_documents({}),
            "indexes": await collection.index_information()
        }
    
    return stats

if __name__ == "__main__":
    asyncio.run(initialize_database())
