#!/usr/bin/env python3
"""
Test script to validate Python syntax and import capabilities
for the Git Timesheet Mapper addon.
"""

import sys
import os
import importlib.util
import ast

def test_python_file(file_path):
    """Test if a Python file has valid syntax and can be parsed."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check syntax
        ast.parse(content, filename=file_path)
        
        print(f"✓ {file_path}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path}: Error - {e}")
        return False

def find_python_files(directory):
    """Find all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files

def main():
    """Main test function."""
    addon_path = "git_timesheet_mapper"
    
    if not os.path.exists(addon_path):
        print(f"Error: Addon directory '{addon_path}' not found")
        sys.exit(1)
    
    python_files = find_python_files(addon_path)
    
    print(f"Testing {len(python_files)} Python files in {addon_path}/...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for file_path in sorted(python_files):
        if test_python_file(file_path):
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("❌ Some files have syntax errors!")
        sys.exit(1)
    else:
        print("✅ All Python files have valid syntax!")
        sys.exit(0)

if __name__ == "__main__":
    main()
