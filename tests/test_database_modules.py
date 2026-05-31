"""
Unit tests for database modules
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bson import ObjectId

class TestDatabaseModules:
    """Test database operations"""
    
    @pytest.fixture
    def mock_mongo_client(self):
        with patch('pymongo.MongoClient') as mock:
            db = Mock()
            mock.return_value.__getitem__.return_value = db
            db.users = Mock()
            db.conversations = Mock()
            db.messages = Mock()
            yield db
    
    @patch('test_mongodb_connection.MongoClient')
    def test_connection_success(self, MockClient):
        """Test successful database connection"""
        from test_mongodb_connection import test_connection
        
        mock_client = MockClient.return_value
        mock_client.server_info.return_value = {"version": "5.0"}
        
        result = test_connection()
        
        assert result is True
        mock_client.server_info.assert_called_once()
    
    @patch('test_mongodb_connection.MongoClient')
    def test_connection_failure(self, MockClient):
        """Test database connection failure"""
        from test_mongodb_connection import test_connection
        
        MockClient.side_effect = Exception("Connection failed")
        
        result = test_connection()
        
        assert result is False
    
    @patch('test_atlas.MongoClient')
    def test_atlas_connection(self, MockClient):
        """Test MongoDB Atlas connection"""
        from test_atlas import test_atlas_connection
        
        mock_client = MockClient.return_value
        mock_client.list_database_names.return_value = ["db1", "db2"]
        
        result = test_atlas_connection()
        
        assert result["success"] is True
        assert "databases" in result
    
    @patch('init_mongodb.create_collections')
    def test_collection_creation(self, mock_create):
        """Test collection creation"""
        from init_mongodb import initialize_db
        
        mock_create.return_value = ["users", "conversations", "messages"]
        
        collections = initialize_db()
        
        assert len(collections) == 3
        assert "users" in collections
    
    def test_object_id_generation(self):
        """Test ObjectId generation"""
        from bson import ObjectId
        
        obj_id = ObjectId()
        
        assert len(str(obj_id)) == 24
        assert isinstance(obj_id.generation_time, datetime)
    
    @patch('connection.get_database')
    def test_db_operations(self, mock_get_db):
        """Test basic database operations"""
        from connection import insert_document, find_document
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.users.insert_one.return_value = Mock(inserted_id="12345")
        
        doc_id = insert_document("users", {"name": "Test"})
        assert doc_id == "12345"
        
        mock_db.users.find_one.return_value = {"name": "Test"}
        doc = find_document("users", {"name": "Test"})
        assert doc is not None
    
    def test_data_validation(self):
        """Test data validation before insertion"""
        from schema import validate_user_data, validate_message_data
        
        valid_user = {
            "username": "testuser",
            "email": "test@example.com",
            "created_at": datetime.now()
        }
        
        invalid_user = {
            "username": "",  # Empty username
            "email": "invalid"
        }
        
        assert validate_user_data(valid_user) is True
        assert validate_user_data(invalid_user) is False
    
    @patch('base_repository.BaseRepository')
    def test_repository_pattern(self, MockRepo):
        """Test repository pattern implementation"""
        mock_repo = MockRepo.return_value
        mock_repo.find_by_id.return_value = {"_id": "123", "name": "Test"}
        
        result = mock_repo.find_by_id("123")
        
        assert result["name"] == "Test"
        mock_repo.find_by_id.assert_called_with("123")
    
    def test_query_building(self):
        """Test query builder functions"""
        from connection import build_query
        
        filters = {"user_id": "123", "status": "active"}
        query = build_query(filters)
        
        assert query["user_id"] == "123"
        assert query["status"] == "active"
    
    @patch('connection.db')
    def test_aggregation_pipeline(self, mock_db):
        """Test aggregation pipeline"""
        from connection import run_aggregation
        
        mock_db.users.aggregate.return_value = [
            {"_id": "$user_id", "count": 10}
        ]
        
        pipeline = [
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
        ]
        
        results = run_aggregation("users", pipeline)
        
        assert len(results) == 1
        assert "count" in results[0]
