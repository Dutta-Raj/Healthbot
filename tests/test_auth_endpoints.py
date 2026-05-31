"""
Unit tests for authentication endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import jwt

class TestAuthEndpoints:
    """Test authentication and authorization"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database connection"""
        with patch('pymongo.MongoClient') as mock_client:
            db = Mock()
            mock_client.return_value.__getitem__.return_value = db
            db.users = Mock()
            db.sessions = Mock()
            yield db
    
    @pytest.fixture
    def sample_user(self):
        """Sample user data"""
        return {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "role": "patient"
        }
    
    def test_hash_password(self):
        """Test password hashing function"""
        from auth_endpoints import hash_password, verify_password
        
        password = "MySecretPassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 20
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_hash_password_different_salts(self):
        """Test that same password produces different hashes"""
        from auth_endpoints import hash_password
        
        password = "SamePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts should produce different hashes
    
    def test_create_jwt_token(self):
        """Test JWT token creation"""
        from auth_endpoints import create_access_token
        
        user_id = "user_12345"
        token = create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        
        # Decode and verify
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded['user_id'] == user_id
        assert 'exp' in decoded
        assert 'iat' in decoded
    
    def test_jwt_token_with_expiry(self):
        """Test JWT token with custom expiry"""
        from auth_endpoints import create_access_token
        
        user_id = "user123"
        # Create token that expires in 5 minutes
        token = create_access_token(user_id, expires_delta=timedelta(minutes=5))
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_time = datetime.fromtimestamp(decoded['exp'])
        iat_time = datetime.fromtimestamp(decoded['iat'])
        
        assert (exp_time - iat_time).seconds == 300  # 5 minutes
    
    def test_verify_valid_token(self):
        """Test verifying a valid token"""
        from auth_endpoints import create_access_token, verify_token
        
        user_id = "test_user"
        token = create_access_token(user_id)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload['user_id'] == user_id
    
    def test_verify_expired_token(self):
        """Test verifying an expired token"""
        from auth_endpoints import create_access_token, verify_token
        
        # Create token that expired 1 second ago
        token = create_access_token("user123", expires_delta=timedelta(seconds=-1))
        payload = verify_token(token)
        
        assert payload is None  # Should return None for expired token
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token"""
        from auth_endpoints import verify_token
        
        invalid_token = "this.is.not.a.valid.token"
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    @patch('auth_endpoints.collection')
    def test_register_user_success(self, mock_db, sample_user):
        """Test successful user registration"""
        from auth_endpoints import register_user
        
        mock_db.users.find_one.return_value = None  # User doesn't exist
        mock_db.users.insert_one.return_value = Mock(inserted_id="67890")
        
        result = register_user(sample_user)
        
        assert result['status'] == 'success'
        assert 'user_id' in result
        assert result['user_id'] == "67890"
        mock_db.users.insert_one.assert_called_once()
    
    @patch('auth_endpoints.collection')
    def test_register_duplicate_user(self, mock_db, sample_user):
        """Test registration with existing username"""
        from auth_endpoints import register_user
        
        mock_db.users.find_one.return_value = sample_user
        
        with pytest.raises(Exception) as exc_info:
            register_user(sample_user)
        
        assert "already exists" in str(exc_info.value).lower()
    
    @patch('auth_endpoints.collection')
    def test_register_invalid_email(self, mock_db):
        """Test registration with invalid email"""
        from auth_endpoints import register_user
        
        invalid_user = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "SecurePass123!"
        }
        
        mock_db.users.find_one.return_value = None
        
        with pytest.raises(Exception) as exc_info:
            register_user(invalid_user)
        
        assert "email" in str(exc_info.value).lower()
    
    @patch('auth_endpoints.collection')
    def test_login_success(self, mock_db):
        """Test successful login"""
        from auth_endpoints import login_user, hash_password
        
        password = "correctpassword"
        hashed_password = hash_password(password)
        
        mock_user = {
            "username": "testuser",
            "password": hashed_password,
            "email": "test@example.com",
            "user_id": "12345"
        }
        mock_db.users.find_one.return_value = mock_user
        
        result = login_user("testuser", password)
        
        assert result['status'] == 'success'
        assert 'token' in result
        assert 'user_id' in result
    
    @patch('auth_endpoints.collection')
    def test_login_wrong_password(self, mock_db):
        """Test login with wrong password"""
        from auth_endpoints import login_user, hash_password
        
        hashed_password = hash_password("correctpassword")
        
        mock_user = {
            "username": "testuser",
            "password": hashed_password
        }
        mock_db.users.find_one.return_value = mock_user
        
        with pytest.raises(Exception) as exc_info:
            login_user("testuser", "wrongpassword")
        
        assert "invalid" in str(exc_info.value).lower()
    
    @patch('auth_endpoints.collection')
    def test_login_user_not_found(self, mock_db):
        """Test login with non-existent user"""
        from auth_endpoints import login_user
        
        mock_db.users.find_one.return_value = None
        
        with pytest.raises(Exception) as exc_info:
            login_user("nonexistent", "password")
        
        assert "not found" in str(exc_info.value).lower()

# Test password strength validation
    def test_password_strength_valid(self):
        """Test valid password strength"""
        from auth_endpoints import validate_password_strength
        
        valid_passwords = [
            "SecurePass123!",
            "Complex@Password456",
            "Str0ng#Pass789",
            "V3ry$trongP@ssw0rd"
        ]
        
        for password in valid_passwords:
            assert validate_password_strength(password) is True
    
    def test_password_strength_invalid(self):
        """Test invalid password strength"""
        from auth_endpoints import validate_password_strength
        
        invalid_passwords = [
            "weak",
            "onlylowercase",
            "ONLYUPPERCASE",
            "1234567890",
            "no special chars"
        ]
        
        for password in invalid_passwords:
            assert validate_password_strength(password) is False
