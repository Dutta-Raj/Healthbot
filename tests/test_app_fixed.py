# test_app_fixed.py
import pytest
import json
import bcrypt
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add current directory to path to import app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from app instead of main
from app import app, validate_email, validate_password, validate_name

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Unit Tests for Utility Functions ---
def test_validate_email():
    """Test email validation function"""
    assert validate_email("test@example.com") == True
    assert validate_email("invalid-email") == False
    assert validate_email("") == False
    assert validate_email("test@domain") == False

def test_validate_password():
    """Test password validation function"""
    assert validate_password("123456") == True
    assert validate_password("short") == False
    assert validate_password("") == False

def test_validate_name():
    """Test name validation function"""
    assert validate_name("John") == True
    assert validate_name("A") == False
    assert validate_name("") == False
    assert validate_name("  ") == False

# --- Unit Tests for Routes ---
def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
    assert 'database' in response.json
    assert 'ai_service' in response.json

def test_home_route(client):
    """Test home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'HealthQ' in response.data

def test_debug_db_no_connection(client):
    """Test debug endpoint when no database connection"""
    # Patch the correct module - app instead of main
    with patch('app.users_collection', None):
        response = client.get('/debug-db')
        assert response.status_code == 200
        assert response.json['database_status'] == 'not_connected'

# --- Authentication Tests ---

# All patches updated to use 'app' instead of 'main'
@patch('app.users_collection')
def test_register_missing_fields(mock_users, client):
    """Test registration with missing fields"""
    response = client.post('/register', json={
        'password': 'password123',
        'name': 'John Doe'
    })
    assert response.status_code == 400
    assert 'required' in response.json['error'].lower()

@patch('app.users_collection')
def test_register_invalid_email(mock_users, client):
    """Test registration with invalid email"""
    mock_users.find_one.return_value = None
    
    response = client.post('/register', json={
        'email': 'invalid-email',
        'password': 'password123',
        'name': 'John Doe'
    })
    assert response.status_code == 400
    assert 'invalid email' in response.json['error'].lower()

@patch('app.users_collection')
def test_register_weak_password(mock_users, client):
    """Test registration with weak password"""
    mock_users.find_one.return_value = None
    
    response = client.post('/register', json={
        'email': 'test@example.com',
        'password': '123',
        'name': 'John Doe'
    })
    assert response.status_code == 400
    assert 'password' in response.json['error'].lower()

@patch('app.users_collection')
def test_register_existing_user(mock_users, client):
    """Test registration with existing email"""
    mock_users.find_one.return_value = {'email': 'test@example.com'}
    
    response = client.post('/register', json={
        'email': 'test@example.com',
        'password': 'password123',
        'name': 'John Doe'
    })
    assert response.status_code == 400
    assert 'already exists' in response.json['error'].lower()

@patch('app.users_collection')
def test_register_success(mock_users, client):
    """Test successful user registration"""
    mock_users.find_one.return_value = None
    mock_users.insert_one.return_value.inserted_id = '507f1f77bcf86cd799439011'
    
    response = client.post('/register', json={
        'email': 'test@example.com',
        'password': 'password123',
        'name': 'John Doe'
    })
    
    assert response.status_code == 201
    assert 'successfully' in response.json['message'].lower()
    assert 'token' in response.json

@patch('app.users_collection')
def test_login_missing_credentials(mock_users, client):
    """Test login with missing credentials"""
    response = client.post('/login', json={})
    assert response.status_code == 400
    assert 'required' in response.json['error'].lower()

@patch('app.users_collection')
def test_login_user_not_found(mock_users, client):
    """Test login with non-existent user"""
    mock_users.find_one.return_value = None
    
    response = client.post('/login', json={
        'email': 'nonexistent@example.com',
        'password': 'password123'
    })
    assert response.status_code == 401
    assert 'invalid' in response.json['error'].lower()

@patch('app.users_collection')
def test_login_wrong_password(mock_users, client):
    """Test login with wrong password"""
    hashed_password = bcrypt.hashpw(b'correctpassword', bcrypt.gensalt())
    mock_users.find_one.return_value = {
        '_id': '507f1f77bcf86cd799439011',
        'email': 'test@example.com',
        'password': hashed_password,
        'name': 'John Doe'
    }
    
    response = client.post('/login', json={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
    assert 'invalid' in response.json['error'].lower()

@patch('app.users_collection')
def test_login_success(mock_users, client):
    """Test successful login"""
    correct_password = 'password123'
    hashed_password = bcrypt.hashpw(correct_password.encode('utf-8'), bcrypt.gensalt())
    mock_users.find_one.return_value = {
        '_id': '507f1f77bcf86cd799439011',
        'email': 'test@example.com',
        'password': hashed_password,
        'name': 'John Doe'
    }
    
    response = client.post('/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    assert 'successful' in response.json['message'].lower()
    assert 'token' in response.json

# --- Protected Routes Tests ---
def test_protected_route_missing_token(client):
    """Test accessing protected route without token"""
    response = client.get('/history')
    assert response.status_code == 401
    assert 'token' in response.json['error'].lower()

def test_protected_route_invalid_token(client):
    """Test accessing protected route with invalid token"""
    response = client.get('/history', headers={
        'Authorization': 'Bearer invalid_token'
    })
    assert response.status_code == 401
    assert 'invalid' in response.json['error'].lower()

def test_chat_without_authentication(client):
    """Test chat endpoint without authentication"""
    response = client.post('/chat', json={'message': 'Hello'})
    assert response.status_code == 401

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
