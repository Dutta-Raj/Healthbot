# run_final_tests.py
import subprocess
import sys

print("\n" + "="*50)
print("CHATBOT PROJECT TESTS")
print("="*50)

# Run the final tests
result = subprocess.run([sys.executable, "final_tests.py"])
sys.exit(result.returncode)
