# database/healthbot_db.py
"""
Complete MongoDB Atlas Integration for HealthBot AI
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

class HealthBotDatabase:
    def __init__(self):
        username = os.getenv('MONGO_USERNAME')
        password = os.getenv('MONGO_PASSWORD')
        cluster = os.getenv('MONGO_CLUSTER')
        db_name = os.getenv('MONGO_DB_NAME', 'myappdb')
        
        if not all([username, password, cluster]):
            print("⚠️ MongoDB credentials missing, using in-memory storage")
            self.available = False
            return
        
        connection_string = f'mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority'
        
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
            self.available = True
            print("✅ HealthBot AI connected to MongoDB Atlas")
            self._setup_collections_and_indexes()
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            self.available = False
    
    def _setup_collections_and_indexes(self):
        """Setup all collections with optimized indexes"""
        
        # 1. Users Collection
        if 'users' not in self.db.list_collection_names():
            self.db.create_collection('users')
        
        users = self.db.users
        users.create_index([('email', ASCENDING)], unique=True)
        users.create_index([('email', ASCENDING), ('is_active', ASCENDING)])
        users.create_index([('created_at', DESCENDING)])
        users.create_index([('full_name', 'text'), ('email', 'text')])
        print("  ✓ Users collection ready")
        
        # 2. Conversations Collection
        if 'conversations' not in self.db.list_collection_names():
            self.db.create_collection('conversations')
        
        conv = self.db.conversations
        conv.create_index([('user_id', ASCENDING), ('started_at', DESCENDING)])
        conv.create_index([('status', ASCENDING), ('updated_at', DESCENDING)])
        conv.create_index([('user_id', ASCENDING), ('external_id', ASCENDING)], unique=True, sparse=True)
        print("  ✓ Conversations collection ready")
        
        # 3. Messages Collection
        if 'messages' not in self.db.list_collection_names():
            self.db.create_collection('messages')
        
        msgs = self.db.messages
        msgs.create_index([('conversation_id', ASCENDING), ('created_at', ASCENDING)])
        msgs.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
        msgs.create_index([('conversation_id', ASCENDING), ('message_type', ASCENDING)])
        msgs.create_index([('content', 'text')])
        print("  ✓ Messages collection ready")
        
        # 4. Medical Knowledge Collection (for RAG)
        if 'medical_knowledge' not in self.db.list_collection_names():
            self.db.create_collection('medical_knowledge')
        
        medical = self.db.medical_knowledge
        medical.create_index([('category', ASCENDING), ('subcategory', ASCENDING)])
        medical.create_index([('title', 'text'), ('content', 'text'), ('tags', 'text')])
        medical.create_index([('tags', ASCENDING)])
        print("  ✓ Medical Knowledge collection ready")
        
        # 5. User Feedback Collection
        if 'feedback' not in self.db.list_collection_names():
            self.db.create_collection('feedback')
        
        feedback = self.db.feedback
        feedback.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
        feedback.create_index([('rating', ASCENDING)])
        print("  ✓ Feedback collection ready")
        
        print("✅ All collections and indexes setup complete")
    
    # ============ USER METHODS ============
    def create_user(self, email, full_name, password_hash=None):
        """Create a new user"""
        if not self.available:
            return None
        
        user_data = {
            'email': email,
            'full_name': full_name,
            'password_hash': password_hash,
            'is_active': True,
            'is_verified': False,
            'created_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'preferences': {}
        }
        
        try:
            result = self.db.users.insert_one(user_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        if not self.available:
            return None
        
        return self.db.users.find_one({'email': email})
    
    def update_user_active(self, user_id):
        """Update user's last active timestamp"""
        if not self.available:
            return
        
        self.db.users.update_one(
            {'_id': user_id},
            {'': {'last_active': datetime.utcnow()}}
        )
    
    # ============ CONVERSATION METHODS ============
    def create_conversation(self, user_id, title=None):
        """Create a new conversation"""
        if not self.available:
            return None
        
        conv_data = {
            'user_id': user_id,
            'title': title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            'status': 'active',
            'started_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'message_count': 0
        }
        
        result = self.db.conversations.insert_one(conv_data)
        return str(result.inserted_id)
    
    def get_user_conversations(self, user_id, limit=50):
        """Get all conversations for a user"""
        if not self.available:
            return []
        
        conversations = self.db.conversations.find(
            {'user_id': user_id, 'status': 'active'}
        ).sort('updated_at', DESCENDING).limit(limit)
        
        return list(conversations)
    
    def get_conversation(self, conversation_id):
        """Get conversation by ID"""
        if not self.available:
            return None
        
        from bson import ObjectId
        return self.db.conversations.find_one({'_id': ObjectId(conversation_id)})
    
    # ============ MESSAGE METHODS ============
    def save_message(self, conversation_id, user_id, content, message_type='user'):
        """Save a message to conversation"""
        if not self.available:
            return None
        
        message_data = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'content': content,
            'message_type': message_type,
            'created_at': datetime.utcnow()
        }
        
        result = self.db.messages.insert_one(message_data)
        
        # Update conversation message count and last update
        self.db.conversations.update_one(
            {'_id': conversation_id},
            {
                '': {'message_count': 1},
                '': {'updated_at': datetime.utcnow()}
            }
        )
        
        return str(result.inserted_id)
    
    def get_conversation_messages(self, conversation_id, limit=100):
        """Get all messages in a conversation"""
        if not self.available:
            return []
        
        messages = self.db.messages.find(
            {'conversation_id': conversation_id}
        ).sort('created_at', ASCENDING).limit(limit)
        
        return list(messages)
    
    def get_conversation_history_for_llm(self, conversation_id, limit=10):
        """Get formatted conversation history for LLM context"""
        if not self.available:
            return []
        
        messages = self.db.messages.find(
            {'conversation_id': conversation_id}
        ).sort('created_at', DESCENDING).limit(limit)
        
        # Format for LLM
        history = []
        for msg in sorted(list(messages), key=lambda x: x['created_at']):
            role = 'user' if msg['message_type'] == 'user' else 'assistant'
            history.append({'role': role, 'content': msg['content']})
        
        return history
    
    # ============ MEDICAL KNOWLEDGE METHODS ============
    def add_medical_knowledge(self, title, content, category, tags, confidence=0.8):
        """Add medical knowledge to database"""
        if not self.available:
            return None
        
        knowledge_data = {
            'title': title,
            'content': content,
            'category': category,
            'tags': tags,
            'confidence_score': confidence,
            'created_at': datetime.utcnow(),
            'usage_count': 0
        }
        
        result = self.db.medical_knowledge.insert_one(knowledge_data)
        return str(result.inserted_id)
    
    def search_medical_knowledge(self, query, limit=5):
        """Search medical knowledge using text search"""
        if not self.available:
            return []
        
        results = self.db.medical_knowledge.find(
            {'': {'': query}}
        ).sort([('confidence_score', DESCENDING)]).limit(limit)
        
        return list(results)
    
    def get_medical_by_category(self, category, limit=20):
        """Get medical knowledge by category"""
        if not self.available:
            return []
        
        results = self.db.medical_knowledge.find(
            {'category': category}
        ).sort([('confidence_score', DESCENDING)]).limit(limit)
        
        return list(results)
    
    # ============ FEEDBACK METHODS ============
    def save_feedback(self, user_id, conversation_id, rating, comments=None):
        """Save user feedback"""
        if not self.available:
            return None
        
        feedback_data = {
            'user_id': user_id,
            'conversation_id': conversation_id,
            'rating': rating,
            'comments': comments,
            'created_at': datetime.utcnow()
        }
        
        result = self.db.feedback.insert_one(feedback_data)
        return str(result.inserted_id)
    
    def get_feedback_stats(self):
        """Get feedback statistics"""
        if not self.available:
            return {}
        
        total = self.db.feedback.count_documents({})
        avg_rating = self.db.feedback.aggregate([
            {'': {'_id': None, 'avg': {'': ''}}}
        ])
        
        return {
            'total_feedback': total,
            'average_rating': next(avg_rating, {}).get('avg', 0)
        }
    
    # ============ ANALYTICS METHODS ============
    def get_user_activity_stats(self, days=30):
        """Get user activity statistics"""
        if not self.available:
            return {}
        
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        active_users = self.db.users.count_documents({'last_active': {'': cutoff}})
        total_conversations = self.db.conversations.count_documents({'started_at': {'': cutoff}})
        total_messages = self.db.messages.count_documents({'created_at': {'': cutoff}})
        
        return {
            'active_users': active_users,
            'conversations': total_conversations,
            'messages': total_messages,
            'period_days': days
        }

# Create global instance
db = HealthBotDatabase()
