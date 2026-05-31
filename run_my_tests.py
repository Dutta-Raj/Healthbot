# run_my_tests.py
"""
Simple script to run all tests
"""

import subprocess
import sys

def run_test(test_file):
    """Run a single test file"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)
    result = subprocess.run([sys.executable, test_file], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def main():
    """Run all test files"""
    test_files = [
        "test_basic.py",
        "test_comprehensive_working.py"
    ]
    
    all_passed = True
    for test_file in test_files:
        if not run_test(test_file):
            all_passed = False
            print(f"❌ {test_file} failed")
        else:
            print(f"✅ {test_file} passed")
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
