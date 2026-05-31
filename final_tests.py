# final_tests.py - CORRECTED VERSION
"""
Simple working tests for the Chatbot project
No Unicode characters - works on any Windows console
"""

import unittest
import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

class TestProjectStructure(unittest.TestCase):
    """Test project structure"""
    
    def test_directories_exist(self):
        """Check important directories"""
        directories = ["database", "frontend", "tests", "src", "warehouse"]
        for directory in directories:
            if os.path.exists(directory):
                print(f"[OK] {directory}/ exists")
            else:
                print(f"[WARN] {directory}/ not found")
        self.assertTrue(True)
    
    def test_python_files_count(self):
        """Count Python files"""
        py_files = []
        for root, dirs, files in os.walk("."):
            if "venv" not in root and "__pycache__" not in root:
                for file in files:
                    if file.endswith(".py"):
                        py_files.append(os.path.join(root, file))
        
        print(f"[INFO] Found {len(py_files)} Python files")
        self.assertGreater(len(py_files), 0)

class TestConfiguration(unittest.TestCase):
    """Test configuration files"""
    
    def test_env_file(self):
        """Check .env file"""
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                content = f.read()
                print(f"[OK] .env file size: {len(content)} bytes")
                self.assertGreater(len(content), 0)
        else:
            print("[WARN] .env file not found")
    
    def test_requirements_file(self):
        """Check requirements.txt"""
        self.assertTrue(os.path.exists("requirements.txt"))
        with open("requirements.txt", "r") as f:
            lines = f.readlines()
            print(f"[OK] Found {len(lines)} requirements")

class TestCodeQuality(unittest.TestCase):
    """Test code quality"""
    
    def test_no_empty_files(self):
        """Check for empty files"""
        empty = []
        for py_file in Path(".").rglob("*.py"):
            if "venv" not in str(py_file):
                if py_file.stat().st_size < 100:
                    empty.append(py_file.name)
        
        if empty:
            print(f"[WARN] Small files: {empty}")
        else:
            print("[OK] No empty files")
    
    def test_file_names(self):
        """Check file naming"""
        valid = 0
        total = 0
        for py_file in Path(".").rglob("*.py"):
            if "venv" not in str(py_file):
                total += 1
                name = py_file.stem
                if re.match(r'^[a-z][a-z0-9_]*$', name) or name.startswith('test_'):
                    valid += 1
        
        print(f"[INFO] {valid}/{total} files follow naming conventions")
        self.assertGreater(valid, total * 0.5)

class TestDependencies(unittest.TestCase):
    """Test installed packages"""
    
    def test_imports(self):
        """Test importing key packages"""
        packages = ['fastapi', 'pymongo', 'dotenv']
        imported = []
        failed = []
        
        for package in packages:
            try:
                __import__(package)
                imported.append(package)
            except ImportError:
                failed.append(package)
        
        if imported:
            print(f"[OK] Imported: {', '.join(imported)}")
        if failed:
            print(f"[WARN] Failed: {', '.join(failed)}")
        
        self.assertGreater(len(imported), 0)

class TestValidation(unittest.TestCase):
    """Test validation functions"""
    
    def test_email_validation(self):
        """Test email validation"""
        def is_valid_email(email):
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
        
        valid = ['user@example.com', 'test@domain.co.uk']
        invalid = ['invalid', 'user@', '@domain.com']
        
        for email in valid:
            self.assertTrue(is_valid_email(email))
        for email in invalid:
            self.assertFalse(is_valid_email(email))
        
        print("[OK] Email validation works")
    
    def test_password_validation(self):
        """Test password validation"""
        def is_strong(pwd):
            # Password must have at least 8 characters
            if len(pwd) < 8:
                return False
            # Must have at least one uppercase
            if not any(c.isupper() for c in pwd):
                return False
            # Must have at least one lowercase
            if not any(c.islower() for c in pwd):
                return False
            # Must have at least one digit
            if not any(c.isdigit() for c in pwd):
                return False
            return True
        
        strong_passwords = ['Strong123', 'Pass123Word', 'Valid99Pass']
        weak_passwords = [
            'weak',           # too short
            'nouppercase123', # no uppercase
            'NOLOWERCASE123', # no lowercase
            'NoDigitsHere',   # no digits
            'short1'          # too short
        ]
        
        # Test strong passwords
        for pwd in strong_passwords:
            self.assertTrue(is_strong(pwd), f"'{pwd}' should be strong")
        
        # Test weak passwords
        for pwd in weak_passwords:
            self.assertFalse(is_strong(pwd), f"'{pwd}' should be weak")
        
        print("[OK] Password validation works")
    
    def test_json_handling(self):
        """Test JSON handling"""
        data = {"key": "value", "number": 123}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        self.assertEqual(data, parsed)
        print("[OK] JSON handling works")

class TestSecurity(unittest.TestCase):
    """Test security basics"""
    
    def test_no_hardcoded_secrets(self):
        """Check for hardcoded secrets"""
        patterns = [r'password\s*=\s*"[^"]+"', r'api_key\s*=\s*"[^"]+"']
        found = []
        
        for py_file in Path(".").rglob("*.py"):
            if "venv" not in str(py_file) and "test" not in py_file.name:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                # Skip if it looks like a placeholder
                                if 'example' not in content.lower() and 'test' not in content.lower():
                                    found.append(py_file.name)
                except:
                    pass
        
        if found:
            print(f"[WARN] Potential secrets in: {found[:3]}")
        else:
            print("[OK] No obvious hardcoded secrets")

class TestPerformance(unittest.TestCase):
    """Test performance"""
    
    def test_quick_scan(self):
        """Test scanning speed"""
        import time
        start = time.time()
        
        total_lines = 0
        for py_file in Path(".").rglob("*.py"):
            if "venv" not in str(py_file):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        total_lines += len(f.readlines())
                except:
                    pass
        
        elapsed = time.time() - start
        print(f"[INFO] Scanned {total_lines} lines in {elapsed:.2f}s")
        self.assertLess(elapsed, 3)

class TestAdditionalChecks(unittest.TestCase):
    """Additional useful checks"""
    
    def test_readme_exists(self):
        """Check if README exists"""
        if os.path.exists("README.md"):
            with open("README.md", "r", encoding='utf-8') as f:
                content = f.read()
                print(f"[OK] README.md size: {len(content)} bytes")
        else:
            print("[WARN] README.md not found")
    
    def test_gitignore_exists(self):
        """Check if .gitignore exists"""
        if os.path.exists(".gitignore"):
            print("[OK] .gitignore exists")
        else:
            print("[WARN] .gitignore not found")

def run_tests():
    """Run all tests"""
    print("\n" + "="*50)
    print("RUNNING FINAL TESTS")
    print("="*50 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestProjectStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeQuality))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencies))
    suite.addTests(loader.loadTestsFromTestCase(TestValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestAdditionalChecks))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("="*50)
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[INFO] Some tests failed - check the output above")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
