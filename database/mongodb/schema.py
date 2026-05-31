# database/mongodb/schema.py
"""
Advanced MongoDB Schema with Optimized Indexing
For HealthBot AI Medical Chatbot
"""

from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT, GEO2D
from pymongo.operations import IndexModel
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Dict, Any
from database.mongodb.connection import mongodb
import logging

logger = logging.getLogger(__name__)

class MongoDBIndexes:
    """All optimized indexes for HealthBot AI"""
    
    @staticmethod
    async def create_user_indexes(collection):
        """Create indexes for Users collection"""
        indexes = [
            # Primary unique index on email
            IndexModel([("email", ASCENDING)], unique=True, name="idx_email_unique"),
            
            # Compound index for authentication
            IndexModel([("email", ASCENDING), ("is_active", ASCENDING)], name="idx_auth"),
            
            # Index for sorting by creation date
            IndexModel([("created_at", DESCENDING)], name="idx_created_at"),
            
            # Partial index for active users only
            IndexModel(
                [("last_active_at", DESCENDING)],
                partialFilterExpression={"is_active": True},
                name="idx_active_users"
            ),
            
            # Text search index for user lookup
            IndexModel(
                [("full_name", TEXT), ("email", TEXT)],
                default_language="english",
                weights={"full_name": 10, "email": 5},
                name="idx_user_text_search"
            ),
            
            # Wildcard index for flexible user preferences
            IndexModel([("preferences.$**", ASCENDING)], name="idx_preferences"),
            
            # TTL index for temporary users cleanup
            IndexModel(
                [("created_at", ASCENDING)],
                expireAfterSeconds=2592000,  # 30 days
                partialFilterExpression={"is_permanent": False},
                name="idx_temp_users_ttl"
            ),
            
            # Geospatial index for location-based services (future)
            IndexModel([("location", GEO2D)], name="idx_location", sparse=True)
        ]
        
        try:
            await collection.create_indexes(indexes)
            logger.info("✅ User indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating user indexes: {e}")
    
    @staticmethod
    async def create_conversation_indexes(collection):
        """Create indexes for Conversations collection"""
        indexes = [
            # Most common query: get user conversations sorted by date
            IndexModel(
                [("user_id", ASCENDING), ("started_at", DESCENDING), ("status", ASCENDING)],
                name="idx_user_conversations"
            ),
            
            # Index for active conversations monitoring
            IndexModel(
                [("status", ASCENDING), ("updated_at", DESCENDING)],
                name="idx_active_conversations"
            ),
            
            # Unique constraint for external_id per user
            IndexModel(
                [("user_id", ASCENDING), ("external_id", ASCENDING)],
                unique=True,
                name="idx_user_external_id",
                sparse=True
            ),
            
            # Index for date range queries
            IndexModel(
                [("started_at", ASCENDING), ("ended_at", ASCENDING)],
                name="idx_date_range"
            ),
            
            # Index for conversation analysis
            IndexModel(
                [("metadata.total_messages", ASCENDING)],
                name="idx_message_count",
                sparse=True
            ),
            
            # Wildcard for flexible metadata queries
            IndexModel([("metadata.$**", ASCENDING)], name="idx_metadata"),
            
            # Partial index for ongoing conversations
            IndexModel(
                [("user_id", ASCENDING), ("started_at", ASCENDING)],
                partialFilterExpression={"status": "active"},
                name="idx_ongoing_conversations"
            )
        ]
        
        try:
            await collection.create_indexes(indexes)
            logger.info("✅ Conversation indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating conversation indexes: {e}")
    
    @staticmethod
    async def create_message_indexes(collection):
        """Create indexes for Messages collection (most critical for performance)"""
        indexes = [
            # Compound index for conversation timeline
            IndexModel(
                [("conversation_id", ASCENDING), ("created_at", ASCENDING)],
                name="idx_conversation_timeline"
            ),
            
            # Index for user message history
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_user_messages"
            ),
            
            # Text search index for message content
            IndexModel(
                [("content", TEXT)],
                default_language="english",
                weights={"content": 10},
                name="idx_message_content_search"
            ),
            
            # Compound index for filtering by message type
            IndexModel(
                [("message_type", ASCENDING), ("created_at", DESCENDING)],
                name="idx_message_type"
            ),
            
            # Index for vector similarity search (for RAG)
            IndexModel(
                [("embedding", "2dsphere")],
                name="idx_embedding",
                sparse=True
            ),
            
            # Index for analytics queries
            IndexModel(
                [("user_id", ASCENDING), ("message_type", ASCENDING), ("created_at", DESCENDING)],
                name="idx_user_message_analytics"
            ),
            
            # TTL index for temporary message cleanup
            IndexModel(
                [("is_temporary", ASCENDING), ("created_at", ASCENDING)],
                expireAfterSeconds=86400,  # 24 hours
                partialFilterExpression={"is_temporary": True},
                name="idx_temp_messages_ttl"
            ),
            
            # Wildcard for message metadata
            IndexModel([("metadata.$**", ASCENDING)], name="idx_message_metadata")
        ]
        
        try:
            await collection.create_indexes(indexes)
            logger.info("✅ Message indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating message indexes: {e}")
    
    @staticmethod
    async def create_medical_knowledge_indexes(collection):
        """Create indexes for Medical Knowledge collection (RAG optimization)"""
        indexes = [
            # Text search for medical content
            IndexModel(
                [("title", TEXT), ("content", TEXT), ("tags", TEXT)],
                default_language="english",
                weights={"title": 15, "content": 5, "tags": 8},
                name="idx_medical_text_search"
            ),
            
            # Compound index for category filtering
            IndexModel(
                [("category", ASCENDING), ("subcategory", ASCENDING), ("confidence_score", DESCENDING)],
                name="idx_medical_category"
            ),
            
            # Index for vector similarity (for RAG pipeline)
            IndexModel(
                [("embedding", "2dsphere")],
                name="idx_vector_similarity"
            ),
            
            # Index for tag-based queries
            IndexModel([("tags", ASCENDING)], name="idx_tags"),
            
            # Index for source reliability ranking
            IndexModel(
                [("source_reliability", DESCENDING), ("confidence_score", DESCENDING)],
                name="idx_source_reliability"
            ),
            
            # Compound index for common medical queries
            IndexModel(
                [("symptom_type", ASCENDING), ("severity_level", ASCENDING)],
                name="idx_symptom_severity",
                sparse=True
            ),
            
            # Wildcard for medical metadata
            IndexModel([("medical_metadata.$**", ASCENDING)], name="idx_medical_metadata")
        ]
        
        try:
            await collection.create_indexes(indexes)
            logger.info("✅ Medical Knowledge indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating medical knowledge indexes: {e}")
    
    @staticmethod
    async def create_analytics_indexes(collection):
        """Create indexes for Analytics collection"""
        indexes = [
            # Compound index for time-series analytics
            IndexModel(
                [("user_id", ASCENDING), ("event_type", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_user_analytics"
            ),
            
            # Index for real-time monitoring
            IndexModel(
                [("event_type", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_event_monitoring"
            ),
            
            # Index for session analysis
            IndexModel(
                [("session_id", ASCENDING), ("timestamp", ASCENDING)],
                name="idx_session_timeline"
            ),
            
            # TTL index for older analytics data
            IndexModel(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=7776000,  # 90 days
                name="idx_analytics_ttl"
            ),
            
            # Index for aggregation pipelines
            IndexModel(
                [("timestamp", DESCENDING), ("event_type", ASCENDING)],
                name="idx_aggregation_optimized"
            )
        ]
        
        try:
            await collection.create_indexes(indexes)
            logger.info("✅ Analytics indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating analytics indexes: {e}")

class MongoDBSchema:
    """Main schema class to initialize all collections and indexes"""
    
    def __init__(self):
        self.index_manager = MongoDBIndexes()
    
    async def initialize_collections(self):
        """Initialize all collections and create indexes"""
        db = await mongodb.get_db()
        
        # Define collections with validation schemas
        collections_config = {
            "users": {
                "validator": {
                    "\": {
                        "bsonType": "object",
                        "required": ["email", "full_name", "created_at"],
                        "properties": {
                            "email": {"bsonType": "string", "pattern": "^.+@.+$"},
                            "full_name": {"bsonType": "string", "minLength": 2},
                            "age": {"bsonType": "int", "minimum": 0, "maximum": 150},
                            "is_active": {"bsonType": "bool"}
                        }
                    }
                }
            },
            "conversations": {
                "validator": {
                    "\": {
                        "bsonType": "object",
                        "required": ["user_id", "started_at"],
                        "properties": {
                            "status": {"enum": ["active", "archived", "deleted"]}
                        }
                    }
                }
            },
            "messages": {
                "validator": {
                    "\": {
                        "bsonType": "object",
                        "required": ["conversation_id", "user_id", "content", "message_type"],
                        "properties": {
                            "message_type": {"enum": ["user", "assistant", "system"]}
                        }
                    }
                }
            }
        }
        
        for coll_name, config in collections_config.items():
            try:
                # Create collection if not exists
                if coll_name not await db.list_collection_names():
                    await db.create_collection(coll_name, **config)
                    logger.info(f"✅ Created collection: {coll_name}")
            except Exception as e:
                logger.warning(f"Collection {coll_name} already exists or error: {e}")
        
        # Create all indexes
        await self.index_manager.create_user_indexes(db.users)
        await self.index_manager.create_conversation_indexes(db.conversations)
        await self.index_manager.create_message_indexes(db.messages)
        await self.index_manager.create_medical_knowledge_indexes(db.medical_knowledge)
        await self.index_manager.create_analytics_indexes(db.analytics_events)
        
        logger.info("🎉 All MongoDB collections and indexes initialized successfully!")
        
        return db

# Initialize schema
mongo_schema = MongoDBSchema()
