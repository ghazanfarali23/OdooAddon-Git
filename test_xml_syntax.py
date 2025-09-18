#!/usr/bin/env python3
"""
Test script to validate XML files for the Git Timesheet Mapper addon.
"""

import sys
import os
import xml.etree.ElementTree as ET

def test_xml_file(file_path):
    """Test if an XML file is well-formed."""
    try:
        ET.parse(file_path)
        print(f"✓ {file_path}: XML OK")
        return True
    except ET.ParseError as e:
        print(f"✗ {file_path}: XML Parse Error - {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path}: Error - {e}")
        return False

def find_xml_files(directory):
    """Find all XML files in a directory recursively."""
    xml_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    return xml_files

def main():
    """Main test function."""
    addon_path = "git_timesheet_mapper"
    
    if not os.path.exists(addon_path):
        print(f"Error: Addon directory '{addon_path}' not found")
        sys.exit(1)
    
    xml_files = find_xml_files(addon_path)
    
    print(f"Testing {len(xml_files)} XML files in {addon_path}/...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for file_path in sorted(xml_files):
        if test_xml_file(file_path):
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("❌ Some XML files have syntax errors!")
        sys.exit(1)
    else:
        print("✅ All XML files are well-formed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
