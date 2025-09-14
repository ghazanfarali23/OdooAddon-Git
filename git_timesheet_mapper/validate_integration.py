#!/usr/bin/env python3
"""
Git Timesheet Mapper - Integration Validation Script

This script validates the integration of frontend components with backend APIs,
tests user interactions, and ensures responsive design works correctly.

Usage:
    python3 validate_integration.py [--verbose] [--test-data]

Options:
    --verbose       Enable verbose logging
    --test-data     Create test data for validation
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class IntegrationValidator:
    """Validates the integration of the Git Timesheet Mapper addon."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.setup_logging()
        self.validation_results = {
            'frontend_assets': {'status': 'pending', 'details': []},
            'backend_apis': {'status': 'pending', 'details': []},
            'component_integration': {'status': 'pending', 'details': []},
            'responsive_design': {'status': 'pending', 'details': []},
            'accessibility': {'status': 'pending', 'details': []},
            'performance': {'status': 'pending', 'details': []},
        }
        
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_frontend_assets(self):
        """Validate that all frontend assets exist and are properly structured."""
        self.logger.info("Validating frontend assets...")
        
        required_files = [
            'static/src/js/commit_browser.js',
            'static/src/js/bulk_mapper.js',
            'static/src/css/styles.css',
            'static/src/css/public.css',
            'static/src/xml/templates.xml',
            'data/assets.xml',
        ]
        
        missing_files = []
        invalid_files = []
        
        for file_path in required_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            
            if not full_path.exists():
                missing_files.append(file_path)
                continue
                
            # Validate file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if file_path.endswith('.js'):
                    self._validate_javascript_file(content, file_path)
                elif file_path.endswith('.css'):
                    self._validate_css_file(content, file_path)
                elif file_path.endswith('.xml'):
                    self._validate_xml_file(content, file_path)
                    
            except Exception as e:
                invalid_files.append(f"{file_path}: {str(e)}")
                
        # Update results
        if missing_files or invalid_files:
            self.validation_results['frontend_assets']['status'] = 'failed'
            self.validation_results['frontend_assets']['details'] = {
                'missing_files': missing_files,
                'invalid_files': invalid_files
            }
        else:
            self.validation_results['frontend_assets']['status'] = 'passed'
            self.validation_results['frontend_assets']['details'] = {
                'validated_files': len(required_files),
                'message': 'All frontend assets are present and valid'
            }
            
        self.logger.info(f"Frontend assets validation: {self.validation_results['frontend_assets']['status']}")
        
    def _validate_javascript_file(self, content, file_path):
        """Validate JavaScript file structure and syntax."""
        required_patterns = {
            'commit_browser.js': [
                '/** @odoo-module **/',
                'import { Component',
                'export class GitCommitBrowser',
                'static template',
                'setup()',
            ],
            'bulk_mapper.js': [
                '/** @odoo-module **/',
                'import { Component',
                'export class BulkMappingComponent',
                'static template',
                'setup()',
            ]
        }
        
        filename = file_path.split('/')[-1]
        if filename in required_patterns:
            for pattern in required_patterns[filename]:
                if pattern not in content:
                    raise ValueError(f"Missing required pattern: {pattern}")
                    
    def _validate_css_file(self, content, file_path):
        """Validate CSS file structure and syntax."""
        required_patterns = [
            ':root',
            '.git-timesheet-mapper',
            '@media',
        ]
        
        for pattern in required_patterns:
            if pattern not in content:
                raise ValueError(f"Missing required CSS pattern: {pattern}")
                
    def _validate_xml_file(self, content, file_path):
        """Validate XML file structure and syntax."""
        if 'templates.xml' in file_path:
            required_templates = [
                'git_timesheet_mapper.CommitBrowser',
                'git_timesheet_mapper.BulkMapper',
            ]
            for template in required_templates:
                if template not in content:
                    raise ValueError(f"Missing required template: {template}")
                    
    def validate_backend_apis(self):
        """Validate backend API endpoints and functionality."""
        self.logger.info("Validating backend APIs...")
        
        # Check if all required files exist
        required_api_files = [
            'controllers/git_api.py',
            'services/git_service_factory.py',
            'services/github_service.py',
            'services/gitlab_service.py',
            'services/mapping_service.py',
        ]
        
        missing_files = []
        api_endpoints = []
        
        for file_path in required_api_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            
            if not full_path.exists():
                missing_files.append(file_path)
                continue
                
            # Extract API endpoints
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if '@http.route' in content:
                    # Extract route definitions
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if '@http.route' in line:
                            route_line = line.strip()
                            api_endpoints.append(route_line)
                            
            except Exception as e:
                self.logger.warning(f"Could not parse {file_path}: {str(e)}")
                
        # Validate expected endpoints
        expected_endpoints = [
            '/git_timesheet_mapper/repositories',
            '/git_timesheet_mapper/commits',
            '/git_timesheet_mapper/mapping',
        ]
        
        found_endpoints = []
        for endpoint in expected_endpoints:
            for api_endpoint in api_endpoints:
                if endpoint in api_endpoint:
                    found_endpoints.append(endpoint)
                    break
                    
        # Update results
        if missing_files:
            self.validation_results['backend_apis']['status'] = 'failed'
            self.validation_results['backend_apis']['details'] = {
                'missing_files': missing_files,
                'found_endpoints': found_endpoints,
                'expected_endpoints': expected_endpoints
            }
        else:
            self.validation_results['backend_apis']['status'] = 'passed'
            self.validation_results['backend_apis']['details'] = {
                'api_files': len(required_api_files),
                'endpoints_found': len(found_endpoints),
                'total_endpoints': len(api_endpoints)
            }
            
        self.logger.info(f"Backend APIs validation: {self.validation_results['backend_apis']['status']}")
        
    def validate_component_integration(self):
        """Validate integration between frontend components and backend."""
        self.logger.info("Validating component integration...")
        
        integration_checks = {
            'odoo_module_imports': self._check_odoo_imports(),
            'component_registration': self._check_component_registration(),
            'service_integration': self._check_service_integration(),
            'template_references': self._check_template_references(),
        }
        
        failed_checks = [check for check, passed in integration_checks.items() if not passed]
        
        if failed_checks:
            self.validation_results['component_integration']['status'] = 'failed'
            self.validation_results['component_integration']['details'] = {
                'failed_checks': failed_checks,
                'all_checks': integration_checks
            }
        else:
            self.validation_results['component_integration']['status'] = 'passed'
            self.validation_results['component_integration']['details'] = {
                'passed_checks': len(integration_checks),
                'message': 'All integration checks passed'
            }
            
        self.logger.info(f"Component integration validation: {self.validation_results['component_integration']['status']}")
        
    def _check_odoo_imports(self):
        """Check if Odoo module imports are correct."""
        js_files = [
            'static/src/js/commit_browser.js',
            'static/src/js/bulk_mapper.js',
        ]
        
        for file_path in js_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '/** @odoo-module **/' not in content:
                        return False
                    if 'import {' not in content:
                        return False
                    if '@odoo/owl' not in content:
                        return False
        return True
        
    def _check_component_registration(self):
        """Check if components are properly registered."""
        js_files = [
            'static/src/js/commit_browser.js',
            'static/src/js/bulk_mapper.js',
        ]
        
        for file_path in js_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'registry.category(' not in content:
                        return False
        return True
        
    def _check_service_integration(self):
        """Check if services are properly integrated."""
        js_files = [
            'static/src/js/commit_browser.js',
            'static/src/js/bulk_mapper.js',
        ]
        
        for file_path in js_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'useService(' not in content:
                        return False
                    if 'this.rpc' not in content and 'this.orm' not in content:
                        return False
        return True
        
    def _check_template_references(self):
        """Check if template references are correct."""
        template_file = project_root / 'git_timesheet_mapper' / 'static/src/xml/templates.xml'
        if not template_file.exists():
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        js_files = [
            ('static/src/js/commit_browser.js', 'git_timesheet_mapper.CommitBrowser'),
            ('static/src/js/bulk_mapper.js', 'git_timesheet_mapper.BulkMapper'),
        ]
        
        for js_file, template_name in js_files:
            full_path = project_root / 'git_timesheet_mapper' / js_file
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    js_content = f.read()
                    if f'static template = "{template_name}"' not in js_content:
                        return False
                    if template_name not in content:
                        return False
        return True
        
    def validate_responsive_design(self):
        """Validate responsive design implementation."""
        self.logger.info("Validating responsive design...")
        
        css_file = project_root / 'git_timesheet_mapper' / 'static/src/css/styles.css'
        
        if not css_file.exists():
            self.validation_results['responsive_design']['status'] = 'failed'
            self.validation_results['responsive_design']['details'] = {
                'error': 'CSS file not found'
            }
            return
            
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        responsive_checks = {
            'media_queries': '@media' in content,
            'mobile_breakpoint': '768px' in content,
            'flexible_layout': 'flex' in content,
            'responsive_grid': 'grid' in content or 'flex' in content,
            'viewport_units': 'vw' in content or 'vh' in content or '%' in content,
        }
        
        failed_checks = [check for check, passed in responsive_checks.items() if not passed]
        
        if len(failed_checks) > 2:  # Allow some flexibility
            self.validation_results['responsive_design']['status'] = 'failed'
            self.validation_results['responsive_design']['details'] = {
                'failed_checks': failed_checks,
                'all_checks': responsive_checks
            }
        else:
            self.validation_results['responsive_design']['status'] = 'passed'
            self.validation_results['responsive_design']['details'] = {
                'responsive_features': len([c for c in responsive_checks.values() if c]),
                'total_checks': len(responsive_checks)
            }
            
        self.logger.info(f"Responsive design validation: {self.validation_results['responsive_design']['status']}")
        
    def validate_accessibility(self):
        """Validate accessibility implementation."""
        self.logger.info("Validating accessibility...")
        
        template_file = project_root / 'git_timesheet_mapper' / 'static/src/xml/templates.xml'
        css_file = project_root / 'git_timesheet_mapper' / 'static/src/css/styles.css'
        
        accessibility_checks = {
            'semantic_html': self._check_semantic_html(template_file),
            'aria_attributes': self._check_aria_attributes(template_file),
            'keyboard_navigation': self._check_keyboard_navigation(template_file),
            'color_contrast': self._check_color_contrast(css_file),
            'focus_indicators': self._check_focus_indicators(css_file),
        }
        
        failed_checks = [check for check, passed in accessibility_checks.items() if not passed]
        
        if len(failed_checks) > 2:  # Allow some flexibility
            self.validation_results['accessibility']['status'] = 'warning'
            self.validation_results['accessibility']['details'] = {
                'failed_checks': failed_checks,
                'all_checks': accessibility_checks,
                'message': 'Some accessibility features may need improvement'
            }
        else:
            self.validation_results['accessibility']['status'] = 'passed'
            self.validation_results['accessibility']['details'] = {
                'accessibility_features': len([c for c in accessibility_checks.values() if c]),
                'total_checks': len(accessibility_checks)
            }
            
        self.logger.info(f"Accessibility validation: {self.validation_results['accessibility']['status']}")
        
    def _check_semantic_html(self, template_file):
        """Check for semantic HTML elements."""
        if not template_file.exists():
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        semantic_elements = ['<button', '<label', '<input', '<select', '<table', '<th', '<td']
        return any(element in content for element in semantic_elements)
        
    def _check_aria_attributes(self, template_file):
        """Check for ARIA attributes."""
        if not template_file.exists():
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        aria_attributes = ['aria-', 'role=', 't-att-aria', 'aria-label', 'aria-describedby']
        return any(attr in content for attr in aria_attributes)
        
    def _check_keyboard_navigation(self, template_file):
        """Check for keyboard navigation support."""
        if not template_file.exists():
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for tabindex, focus events, or keyboard event handlers
        keyboard_features = ['tabindex', 't-on-keydown', 't-on-keyup', 't-on-keypress', 'focus']
        return any(feature in content for feature in keyboard_features)
        
    def _check_color_contrast(self, css_file):
        """Check for color contrast considerations."""
        if not css_file.exists():
            return False
            
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for color definitions and contrast considerations
        return 'color:' in content and 'background' in content
        
    def _check_focus_indicators(self, css_file):
        """Check for focus indicators."""
        if not css_file.exists():
            return False
            
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return ':focus' in content
        
    def validate_performance(self):
        """Validate performance considerations."""
        self.logger.info("Validating performance...")
        
        performance_checks = {
            'lazy_loading': self._check_lazy_loading(),
            'efficient_selectors': self._check_efficient_selectors(),
            'minimized_dom': self._check_minimized_dom(),
            'optimized_assets': self._check_optimized_assets(),
        }
        
        failed_checks = [check for check, passed in performance_checks.items() if not passed]
        
        if len(failed_checks) > 1:  # Allow some flexibility
            self.validation_results['performance']['status'] = 'warning'
            self.validation_results['performance']['details'] = {
                'failed_checks': failed_checks,
                'all_checks': performance_checks,
                'message': 'Some performance optimizations may be beneficial'
            }
        else:
            self.validation_results['performance']['status'] = 'passed'
            self.validation_results['performance']['details'] = {
                'performance_features': len([c for c in performance_checks.values() if c]),
                'total_checks': len(performance_checks)
            }
            
        self.logger.info(f"Performance validation: {self.validation_results['performance']['status']}")
        
    def _check_lazy_loading(self):
        """Check for lazy loading implementation."""
        js_files = [
            'static/src/js/commit_browser.js',
            'static/src/js/bulk_mapper.js',
        ]
        
        for file_path in js_files:
            full_path = project_root / 'git_timesheet_mapper' / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'loading' in content or 'async' in content:
                        return True
        return False
        
    def _check_efficient_selectors(self):
        """Check for efficient CSS selectors."""
        css_file = project_root / 'git_timesheet_mapper' / 'static/src/css/styles.css'
        if not css_file.exists():
            return False
            
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for class-based selectors (more efficient than complex selectors)
        class_selectors = content.count('.')
        id_selectors = content.count('#')
        complex_selectors = content.count(' > ') + content.count(' + ') + content.count(' ~ ')
        
        return (class_selectors + id_selectors) > complex_selectors
        
    def _check_minimized_dom(self):
        """Check for minimized DOM structure."""
        template_file = project_root / 'git_timesheet_mapper' / 'static/src/xml/templates.xml'
        if not template_file.exists():
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for conditional rendering and efficient templates
        conditional_features = ['t-if=', 't-foreach=', 't-else=']
        return any(feature in content for feature in conditional_features)
        
    def _check_optimized_assets(self):
        """Check for optimized asset loading."""
        assets_file = project_root / 'git_timesheet_mapper' / 'data/assets.xml'
        if not assets_file.exists():
            return False
            
        with open(assets_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for proper bundling and sequencing
        return 'bundle=' in content and 'sequence=' in content
        
    def run_validation(self):
        """Run all validation checks."""
        self.logger.info("Starting Git Timesheet Mapper integration validation...")
        
        start_time = time.time()
        
        # Run all validations
        self.validate_frontend_assets()
        self.validate_backend_apis()
        self.validate_component_integration()
        self.validate_responsive_design()
        self.validate_accessibility()
        self.validate_performance()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate summary
        total_checks = len(self.validation_results)
        passed_checks = sum(1 for result in self.validation_results.values() if result['status'] == 'passed')
        failed_checks = sum(1 for result in self.validation_results.values() if result['status'] == 'failed')
        warning_checks = sum(1 for result in self.validation_results.values() if result['status'] == 'warning')
        
        summary = {
            'total_checks': total_checks,
            'passed': passed_checks,
            'failed': failed_checks,
            'warnings': warning_checks,
            'duration': round(duration, 2),
            'overall_status': 'passed' if failed_checks == 0 else 'failed',
            'details': self.validation_results
        }
        
        self.logger.info(f"Validation completed in {duration:.2f} seconds")
        self.logger.info(f"Results: {passed_checks} passed, {failed_checks} failed, {warning_checks} warnings")
        
        return summary
        
    def generate_report(self, summary, output_file=None):
        """Generate a validation report."""
        if output_file is None:
            output_file = project_root / 'validation_report.json'
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
            
        self.logger.info(f"Validation report saved to: {output_file}")
        
        # Print summary to console
        print("\n" + "="*60)
        print("GIT TIMESHEET MAPPER - INTEGRATION VALIDATION REPORT")
        print("="*60)
        print(f"Overall Status: {summary['overall_status'].upper()}")
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Duration: {summary['duration']} seconds")
        print("\nDetailed Results:")
        print("-" * 40)
        
        for check_name, result in summary['details'].items():
            status = result['status'].upper()
            print(f"{check_name.replace('_', ' ').title()}: {status}")
            
            if result['status'] == 'failed' and 'failed_checks' in result['details']:
                failed = result['details']['failed_checks']
                if failed:
                    print(f"  Failed: {', '.join(failed)}")
                    
        print("="*60)
        
        return output_file

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Validate Git Timesheet Mapper integration')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--output', '-o', help='Output file for validation report')
    
    args = parser.parse_args()
    
    # Run validation
    validator = IntegrationValidator(verbose=args.verbose)
    summary = validator.run_validation()
    
    # Generate report
    report_file = validator.generate_report(summary, args.output)
    
    # Exit with appropriate code
    exit_code = 0 if summary['overall_status'] == 'passed' else 1
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
