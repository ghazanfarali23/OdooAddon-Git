#!/usr/bin/env python3
"""
Comprehensive validation script for the Git Timesheet Mapper addon.
Checks for common issues that could cause Odoo module installation failures.
"""

import sys
import os
import ast
import xml.etree.ElementTree as ET
import json
from datetime import datetime

def validate_python_syntax(addon_path):
    """Validate Python syntax in all .py files."""
    print("🐍 Validating Python syntax...")
    python_files = []
    for root, dirs, files in os.walk(addon_path):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content, filename=file_path)
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error parsing {file_path}: {e}")
    
    if errors:
        print("❌ Python syntax errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ All {len(python_files)} Python files have valid syntax")
        return True

def validate_xml_syntax(addon_path):
    """Validate XML syntax in all .xml files."""
    print("\n📄 Validating XML syntax...")
    xml_files = []
    for root, dirs, files in os.walk(addon_path):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    errors = []
    for file_path in xml_files:
        try:
            ET.parse(file_path)
        except ET.ParseError as e:
            errors.append(f"XML parse error in {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error parsing {file_path}: {e}")
    
    if errors:
        print("❌ XML syntax errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ All {len(xml_files)} XML files are well-formed")
        return True

def validate_manifest(addon_path):
    """Validate the addon manifest file."""
    print("\n📋 Validating manifest file...")
    manifest_path = os.path.join(addon_path, '__manifest__.py')
    
    if not os.path.exists(manifest_path):
        print("❌ __manifest__.py file not found")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the manifest - it should be a Python dictionary
        import ast
        tree = ast.parse(content)
        
        # Find the dictionary definition
        manifest = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                # Execute the dictionary to get its value
                manifest = eval(compile(ast.Expression(node), '<string>', 'eval'))
                break
        
        if manifest is None:
            print("❌ No dictionary found in __manifest__.py")
            return False
        
        # Check required fields
        required_fields = ['name', 'version', 'depends', 'data']
        missing_fields = [field for field in required_fields if field not in manifest]
        
        if missing_fields:
            print(f"❌ Missing required manifest fields: {missing_fields}")
            return False
        
        # Check if data files exist
        errors = []
        for data_file in manifest.get('data', []):
            file_path = os.path.join(addon_path, data_file)
            if not os.path.exists(file_path):
                errors.append(f"Data file not found: {data_file}")
        
        # Check if asset files exist
        for asset_bundle, asset_files in manifest.get('assets', {}).items():
            for asset_file in asset_files:
                if asset_file.startswith(f"{os.path.basename(addon_path)}/"):
                    relative_path = asset_file[len(os.path.basename(addon_path))+1:]
                    file_path = os.path.join(addon_path, relative_path)
                    if not os.path.exists(file_path):
                        errors.append(f"Asset file not found: {asset_file}")
        
        if errors:
            print("❌ Manifest validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ Manifest file is valid")
            return True
    
    except Exception as e:
        print(f"❌ Error validating manifest: {e}")
        return False

def check_model_init_methods(addon_path):
    """Check for problematic __init__ methods in Odoo models."""
    print("\n🔧 Checking model __init__ methods...")
    
    python_files = []
    for root, dirs, files in os.walk(addon_path):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    issues = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content, filename=file_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's likely an Odoo model
                    is_odoo_model = False
                    for base in node.bases:
                        if isinstance(base, ast.Attribute):
                            if (isinstance(base.value, ast.Name) and 
                                base.value.id == 'models' and 
                                base.attr in ['Model', 'TransientModel', 'AbstractModel']):
                                is_odoo_model = True
                                break
                    
                    if is_odoo_model:
                        # Check for __init__ method
                        for method in node.body:
                            if (isinstance(method, ast.FunctionDef) and 
                                method.name == '__init__'):
                                
                                # Check parameter count (should be self, env, ids, prefetch_ids)
                                params = method.args.args
                                if len(params) != 4:  # self + 3 Odoo parameters
                                    issues.append(f"Suspicious __init__ method in {file_path}, class {node.name}: expected 4 parameters, got {len(params)}")
        
        except Exception as e:
            # Skip files that can't be parsed
            continue
    
    if issues:
        print("⚠️  Potential __init__ method issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ No problematic __init__ methods detected")
        return True

def validate_directory_structure(addon_path):
    """Validate the addon directory structure."""
    print("\n📁 Validating directory structure...")
    
    # Expected directories
    expected_dirs = ['models', 'views', 'security', 'data']
    existing_dirs = [d for d in os.listdir(addon_path) if os.path.isdir(os.path.join(addon_path, d))]
    
    # Check for important files
    important_files = ['__manifest__.py', '__init__.py']
    missing_files = []
    for file in important_files:
        if not os.path.exists(os.path.join(addon_path, file)):
            missing_files.append(file)
    
    issues = []
    
    if missing_files:
        issues.append(f"Missing important files: {missing_files}")
    
    # Check if models/__init__.py exists
    models_init = os.path.join(addon_path, 'models', '__init__.py')
    if os.path.exists(os.path.join(addon_path, 'models')) and not os.path.exists(models_init):
        issues.append("models/__init__.py file is missing")
    
    if issues:
        print("❌ Directory structure issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Directory structure looks good")
        return True

def main():
    """Main validation function."""
    addon_path = "git_timesheet_mapper"
    
    if not os.path.exists(addon_path):
        print(f"❌ Addon directory '{addon_path}' not found")
        sys.exit(1)
    
    print("🚀 Git Timesheet Mapper - Comprehensive Validation")
    print("=" * 60)
    
    all_checks = [
        validate_directory_structure(addon_path),
        validate_python_syntax(addon_path),
        validate_xml_syntax(addon_path),
        validate_manifest(addon_path),
        check_model_init_methods(addon_path)
    ]
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_checks = sum(all_checks)
    total_checks = len(all_checks)
    
    if passed_checks == total_checks:
        print(f"🎉 All {total_checks} validation checks PASSED!")
        print("✅ The addon should be ready for Odoo installation")
        
        # Save validation report
        report = {
            'timestamp': datetime.now().isoformat(),
            'addon_name': 'git_timesheet_mapper',
            'validation_status': 'PASSED',
            'checks_passed': passed_checks,
            'total_checks': total_checks,
            'issues': []
        }
        
        with open('validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Validation report saved to: validation_report.json")
        sys.exit(0)
        
    else:
        print(f"❌ {total_checks - passed_checks} out of {total_checks} checks FAILED")
        print("🔧 Please fix the issues above before installing the addon")
        sys.exit(1)

if __name__ == "__main__":
    main()
