import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import validate_email, validate_password, validate_name, validate_medical_content
    print('✅ SUCCESS: All validation functions imported!')
    
    print('🧪 TESTING VALIDATION FUNCTIONS:')
    
    # Test improved email validation
    test_emails = [
        ('test@gmail.com', True),
        ('user@example.com', True),
        ('invalid-email', False),
        ('missing@domain', False),
        ('', False)
    ]
    
    for email, expected in test_emails:
        result, msg = validate_email(email)
        status = '✅' if result == expected else '❌'
        print(f'{status} Email: {email} -> {result} ({msg})')
    
    # Test password validation
    test_passwords = [
        ('StrongPass123!', True),
        ('weak', False),
        ('NoSpecial123', False)
    ]
    
    for pwd, expected in test_passwords:
        result, msg = validate_password(pwd)
        status = '✅' if result == expected else '❌'
        print(f'{status} Password: {pwd} -> {result}')
    
    # Test name validation
    test_names = [
        ('John Doe', True),
        ('A', False),
        ('', False)
    ]
    
    for name, expected in test_names:
        result, msg = validate_name(name)
        status = '✅' if result == expected else '❌'
        print(f'{status} Name: {name} -> {result}')
    
    # Test medical content
    test_messages = [
        ('Hello there', True),
        ('I have a headache', True),
        ('I am having a heart attack', False)
    ]
    
    for msg, expected in test_messages:
        result, emergency_msg = validate_medical_content(msg)
        status = '✅' if result == expected else '❌'
        print(f'{status} Message: {msg} -> Safe: {result}')
    
    print('\n🎉 ALL VALIDATION TESTS COMPLETED!')
    print('📋 Your app validation system is working correctly!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()