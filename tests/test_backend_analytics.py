"""
Unit tests for backend analytics
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

class TestBackendAnalytics:
    """Test analytics and logging functionality"""
    
    @pytest.fixture
    def mock_db(self):
        with patch('pymongo.MongoClient') as mock:
            db = Mock()
            mock.return_value.__getitem__.return_value = db
            db.interactions = Mock()
            db.sessions = Mock()
            db.metrics = Mock()
            yield db
    
    @pytest.fixture
    def sample_interaction(self):
        return {
            "user_id": "user_123",
            "session_id": "session_456",
            "query": "What is my blood pressure?",
            "response": "Your blood pressure is 120/80 mmHg",
            "response_time_ms": 245,
            "timestamp": datetime.now().isoformat(),
            "sentiment": "positive",
            "intent": "blood_pressure_query"
        }
    
    @patch('backend_analytics.db')
    def test_log_interaction(self, mock_db, sample_interaction):
        """Test logging user interaction"""
        from backend_analytics import log_interaction
        
        mock_db.interactions.insert_one.return_value = Mock(inserted_id="log_123")
        
        result = log_interaction(sample_interaction)
        
        assert result is not None
        mock_db.interactions.insert_one.assert_called_once()
    
    @patch('backend_analytics.db')
    def test_get_user_history(self, mock_db, sample_interaction):
        """Test retrieving user interaction history"""
        from backend_analytics import get_user_history
        
        mock_db.interactions.find.return_value.sort.return_value.limit.return_value = [
            sample_interaction
        ]
        
        history = get_user_history("user_123", limit=10)
        
        assert len(history) == 1
        assert history[0]['user_id'] == "user_123"
    
    @patch('backend_analytics.db')
    def test_get_analytics_summary(self, mock_db):
        """Test getting analytics summary"""
        from backend_analytics import get_analytics_summary
        
        mock_db.interactions.count_documents.return_value = 100
        mock_db.interactions.distinct.return_value = ["user1", "user2", "user3"]
        
        summary = get_analytics_summary()
        
        assert summary['total_interactions'] == 100
        assert summary['unique_users'] == 3
    
    def test_calculate_average_response_time(self):
        """Test calculating average response time"""
        from backend_analytics import calculate_average_response_time
        
        times = [100, 150, 200, 250, 300]
        avg = calculate_average_response_time(times)
        
        assert avg == 200
    
    def test_calculate_percentiles(self):
        """Test response time percentiles"""
        from backend_analytics import calculate_percentiles
        
        times = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        percentiles = calculate_percentiles(times)
        
        assert percentiles['p50'] == 550  # Median
        assert percentiles['p95'] == 950
        assert percentiles['p99'] == 990
    
    @patch('backend_analytics.db')
    def test_track_session(self, mock_db):
        """Test session tracking"""
        from backend_analytics import start_session, end_session
        
        mock_db.sessions.insert_one.return_value = Mock(inserted_id="session_123")
        
        session_id = start_session("user_123")
        assert session_id is not None
        
        end_session(session_id)
        mock_db.sessions.update_one.assert_called()
    
    @patch('backend_analytics.db')
    def test_get_user_sessions(self, mock_db):
        """Test retrieving user sessions"""
        from backend_analytics import get_user_sessions
        
        mock_db.sessions.find.return_value = [
            {"session_id": "s1", "start_time": datetime.now()},
            {"session_id": "s2", "start_time": datetime.now()}
        ]
        
        sessions = get_user_sessions("user_123")
        
        assert len(sessions) == 2
    
    def test_compute_engagement_score(self):
        """Test computing user engagement score"""
        from backend_analytics import compute_engagement_score
        
        metrics = {
            "interactions": 50,
            "session_duration_minutes": 30,
            "queries_per_session": 10
        }
        
        score = compute_engagement_score(metrics)
        
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    @patch('backend_analytics.db')
    def test_export_analytics_csv(self, mock_db, sample_interaction):
        """Test exporting analytics to CSV"""
        from backend_analytics import export_to_csv
        
        mock_db.interactions.find.return_value = [sample_interaction] * 10
        
        csv_data = export_to_csv(start_date=datetime.now() - timedelta(days=7))
        
        assert csv_data is not None
        assert "user_id" in csv_data
