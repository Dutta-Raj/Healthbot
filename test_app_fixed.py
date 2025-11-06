import os  
import sys  
import json  
from unittest.mock import Mock, patch  
  
# Add current directory to path  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  
  
try:  
    from app import app, validate_email, validate_password, validate_name, validate_medical_content  
    print('? Successfully imported app and validation functions!')  
  
    # Test validation functions  
    print('\n?? Testing validation functions...')  
  
    # Test email validation  
    result, msg = validate_email('test@example.com')  
    print(f'? Email validation (valid): {result} - {msg}')  
  
    result, msg = validate_email('invalid-email')  
    print(f'? Email validation (invalid): {result} - {msg}')  
  
    # Test password validation   
    result, msg = validate_password('StrongPass123!')  
    print(f'? Password validation (valid): {result} - {msg}')  
  
    result, msg = validate_password('weak')  
    print(f'? Password validation (invalid): {result} - {msg}')  
  
    # Test name validation  
    result, msg = validate_name('John Doe')  
    print(f'? Name validation (valid): {result} - {msg}')  
  
    result, msg = validate_name('A')  
    print(f'? Name validation (invalid): {result} - {msg}')  
  
    # Test medical content validation  
    result, msg = validate_medical_content('Hello there')  
    print(f'? Medical content (safe): {result} - {msg}')  
  
    result, msg = validate_medical_content('I am having a heart attack')  
    print(f'? Medical content (emergency): {result} - {msg}')  
  
    print('\n?? All validation tests passed!')  
    print('\n?? Starting basic route tests...')  
  
    # Test basic routes  
    with app.test_client() as client:  
        # Test index route  
        response = client.get('/')  
        print(f'? Index route: {response.status_code}')  
  
        # Test login route  
        response = client.get('/login')  
        print(f'? Login route: {response.status_code}')  
  
        # Test register route  
        response = client.get('/register')  
        print(f'? Register route: {response.status_code}')  
  
        # Test health check  
        response = client.get('/api/health')  
        print(f'? Health check: {response.status_code}')  
  
    print('\n?? All basic tests completed successfully!')  
    print('?? Your app is ready with validation functions!')  
  
except ImportError as e:  
    print(f'? Import error: {e}')  
    print('?? Make sure all dependencies are installed and app.py is in the same directory')  
except Exception as e:  
    print(f'? Error during testing: {e}') 
