# database/repositories/base_repository.py
"""
Base Repository with CRUD operations using MongoDB
"""

from typing import Dict, Any, List, Optional, Generic, TypeVar, Union
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from database.mongodb.connection import mongodb
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseRepository:
    """Base repository for MongoDB operations"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._collection: Optional[AsyncIOMotorCollection] = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get collection instance"""
        if self._collection is None:
            db = await mongodb.get_db()
            self._collection = db[self.collection_name]
        return self._collection
    
    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new document"""
        collection = await self.get_collection()
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        
        result = await collection.insert_one(data)
        return str(result.inserted_id)
    
    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find document by ID"""
        collection = await self.get_collection()
        result = await collection.find_one({"_id": ObjectId(id)})
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find one document matching filter"""
        collection = await self.get_collection()
        result = await collection.find_one(filter)
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def find_many(
        self,
        filter: Dict[str, Any],
        sort: List[tuple] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Find multiple documents with pagination"""
        collection = await self.get_collection()
        cursor = collection.find(filter)
        
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        
        return results
    
    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        upsert: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Update a document by ID"""
        collection = await self.get_collection()
        data['updated_at'] = datetime.utcnow()
        
        result = await collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"\": data},
            return_document=ReturnDocument.AFTER,
            upsert=upsert
        )
        
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def delete(self, id: str) -> bool:
        """Soft delete a document (set deleted flag)"""
        return await self.update(id, {"is_deleted": True, "deleted_at": datetime.utcnow()})
    
    async def hard_delete(self, id: str) -> bool:
        """Permanently delete a document"""
        collection = await self.get_collection()
        result = await collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
    
    async def count(self, filter: Dict[str, Any]) -> int:
        """Count documents matching filter"""
        collection = await self.get_collection()
        return await collection.count_documents(filter)
    
    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline"""
        collection = await self.get_collection()
        results = []
        async for doc in collection.aggregate(pipeline):
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

# Specific repositories
class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("users")
    
    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email (uses index)"""
        return await self.find_one({"email": email})
    
    async def update_last_active(self, user_id: str):
        """Update user's last active timestamp"""
        return await self.update(user_id, {"last_active_at": datetime.utcnow()})
    
    async def get_active_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get active users (uses partial index)"""
        return await self.find_many(
            {"is_active": True, "is_verified": True},
            sort=[("last_active_at", -1)],
            limit=limit
        )

class ConversationRepository(BaseRepository):
    def __init__(self):
        super().__init__("conversations")
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user conversations with pagination (uses compound index)"""
        return await self.find_many(
            {"user_id": user_id, "status": "active"},
            sort=[("started_at", -1)],
            limit=limit,
            skip=offset
        )
    
    async def get_active_conversation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get current active conversation for user"""
        return await self.find_one(
            {"user_id": user_id, "status": "active"}
        )

class MessageRepository(BaseRepository):
    def __init__(self):
        super().__init__("messages")
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        before_timestamp: datetime = None
    ) -> List[Dict[str, Any]]:
        """Get messages in a conversation (uses compound index)"""
        filter = {"conversation_id": conversation_id}
        if before_timestamp:
            filter["created_at"] = {"\": before_timestamp}
        
        return await self.find_many(
            filter,
            sort=[("created_at", 1)],
            limit=limit
        )
    
    async def search_messages(
        self,
        user_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search messages using text index"""
        collection = await self.get_collection()
        cursor = collection.find(
            {
                "user_id": user_id,
                "\": {"\": search_term}
            }
        ).sort([("created_at", -1)]).limit(limit)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        
        return results

class MedicalKnowledgeRepository(BaseRepository):
    def __init__(self):
        super().__init__("medical_knowledge")
    
    async def search_by_symptoms(
        self,
        symptoms: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search medical knowledge by symptoms (using text index)"""
        search_query = " ".join(symptoms)
        collection = await self.get_collection()
        
        cursor = collection.find(
            {"\": {"\": search_query}},
            {"score": {"\": "textScore"}}
        ).sort([("score", {"\": "textScore"}), ("confidence_score", -1)]).limit(limit)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        
        return results
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get medical knowledge by category (uses category index)"""
        return await self.find_many(
            {"category": category},
            sort=[("confidence_score", -1)],
            limit=limit
        )
