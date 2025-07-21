#!/usr/bin/env python3

import sys
import traceback
from io import StringIO

print("Testing planning.py execution step by step...")

# Redirect stderr to capture any warnings/errors
old_stderr = sys.stderr
sys.stderr = captured_err = StringIO()

try:
    print("Reading planning.py file...")
    with open('routes/planning.py', 'r') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    print("Executing the file...")
    
    # Execute line by line to find where it fails
    lines = content.split('\n')
    global_vars = {}
    
    for i, line in enumerate(lines, 1):
        try:
            if line.strip() and not line.strip().startswith('#'):
                exec(line, global_vars)
                if 'router' in global_vars:
                    print(f"✓ Router found at line {i}: {line[:50]}...")
        except Exception as e:
            print(f"❌ Error at line {i}: {line[:100]}")
            print(f"   Error: {e}")
            break
            
    if 'router' in global_vars:
        print("✓ Router successfully created in execution")
    else:
        print("✗ Router not found after execution")
        
except Exception as e:
    print(f"❌ Error during execution: {e}")
    traceback.print_exc()
finally:
    # Restore stderr and show any captured errors
    sys.stderr = old_stderr
    errors = captured_err.getvalue()
    if errors:
        print(f"Captured errors/warnings:\n{errors}")
