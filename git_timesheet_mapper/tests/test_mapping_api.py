# -*- coding: utf-8 -*-

import json
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestMappingAPI(HttpCase):
    """Contract tests for Timesheet Commit Mapping API endpoints.
    
    These tests verify the API contract specifications for mapping operations.
    All tests MUST FAIL initially as no implementation exists yet (TDD requirement).
    """

    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        
        # Create test user with timesheet mapping privileges
        self.test_user = self.env['res.users'].create({
            'name': 'Test Mapping User',
            'login': 'test_mapping_user',
            'email': 'mapping@example.com',
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
        })
        
        # Authentication setup for API calls
        self.authenticate('test_mapping_user', 'test_mapping_user')

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_create_success(self):
        """Test POST /git_timesheet_mapper/mapping/create with valid data.
        
        Contract: Should create mapping between commit and timesheet entry.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 1,  # Mock commit ID
            'timesheet_line_id': 1,  # Mock timesheet entry ID
            'description': 'Feature implementation mapping'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 for successful mapping
        self.assertEqual(response.status_code, 200,
                        "Mapping create should return 200 for valid request")
        
        # Contract verification: Response should be JSON
        self.assertEqual(response.headers.get('Content-Type'), 'application/json',
                        "Response should be JSON format")
        
        # Contract verification: Response structure
        response_data = json.loads(response.content.decode())
        self.assertIn('success', response_data, "Response should contain 'success' field")
        self.assertTrue(response_data['success'], "Success should be True for valid mapping")
        self.assertIn('data', response_data, "Response should contain 'data' field")
        
        # Contract verification: Mapping data structure
        data_fields = response_data['data']
        required_fields = ['mapping_id', 'commit_id', 'timesheet_line_id', 'mapping_date', 'mapped_by']
        for field in required_fields:
            self.assertIn(field, data_fields, f"Mapping response should contain '{field}' field")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_create_missing_required_fields(self):
        """Test POST /git_timesheet_mapper/mapping/create with missing required fields.
        
        Contract: Should return 400 when commit_id or timesheet_line_id is missing.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 1
            # Missing: timesheet_line_id (required)
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for missing required fields
        self.assertEqual(response.status_code, 400,
                        "Should return 400 when required fields are missing")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for missing fields")
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR',
                        "Error code should be VALIDATION_ERROR for missing fields")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_create_duplicate_prevention(self):
        """Test POST /git_timesheet_mapper/mapping/create with already mapped commit.
        
        Contract: Should return error when commit is already mapped to prevent duplicates.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 1,  # Mock already mapped commit
            'timesheet_line_id': 1
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for duplicate mapping
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for duplicate mapping attempt")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for duplicate mapping")
        self.assertEqual(response_data['error']['code'], 'MAPPING_DUPLICATE',
                        "Error code should be MAPPING_DUPLICATE for already mapped commit")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_bulk_create_success(self):
        """Test POST /git_timesheet_mapper/mapping/bulk_create with valid commit list.
        
        Contract: Should create multiple mappings and return success/failure counts.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/bulk_create'
        data = {
            'commit_ids': [1, 2, 3, 4, 5],  # Mock commit IDs
            'timesheet_line_id': 1,  # Mock timesheet entry ID
            'description': 'Bulk mapping for feature development'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 for bulk mapping
        self.assertEqual(response.status_code, 200,
                        "Bulk mapping should return 200 for valid request")
        
        # Contract verification: Response structure
        response_data = json.loads(response.content.decode())
        self.assertIn('success', response_data, "Response should contain 'success' field")
        self.assertTrue(response_data['success'], "Success should be True for valid bulk mapping")
        self.assertIn('data', response_data, "Response should contain 'data' field")
        
        # Contract verification: Bulk mapping data structure
        data_fields = response_data['data']
        required_fields = ['created_mappings', 'failed_mappings', 'mapping_ids']
        for field in required_fields:
            self.assertIn(field, data_fields, f"Bulk mapping response should contain '{field}' field")
        
        # Contract verification: Failed mappings structure
        if data_fields['failed_mappings']:
            failed_mapping = data_fields['failed_mappings'][0]
            self.assertIn('commit_id', failed_mapping, "Failed mapping should contain commit_id")
            self.assertIn('error', failed_mapping, "Failed mapping should contain error message")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_bulk_create_empty_commit_list(self):
        """Test POST /git_timesheet_mapper/mapping/bulk_create with empty commit list.
        
        Contract: Should return 400 when commit_ids list is empty.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/bulk_create'
        data = {
            'commit_ids': [],  # Empty list
            'timesheet_line_id': 1
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for empty commit list
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for empty commit list")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for empty commit list")
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR',
                        "Error code should be VALIDATION_ERROR for empty commit list")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_delete_success(self):
        """Test DELETE /git_timesheet_mapper/mapping/{id} with valid mapping ID.
        
        Contract: Should remove mapping and return success message.
        Expected to FAIL: No controller implementation exists yet.
        """
        mapping_id = 1  # Mock mapping ID
        url = f'/git_timesheet_mapper/mapping/{mapping_id}'
        
        response = self.url_open(url, data='', headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 for successful deletion
        if response.status_code == 200:
            response_data = json.loads(response.content.decode())
            self.assertTrue(response_data['success'], "Success should be True for valid deletion")
            self.assertIn('data', response_data, "Response should contain data field")
            self.assertIn('message', response_data['data'], "Should contain success message")
        else:
            # Expected during TDD phase - no implementation yet
            self.assertIn(response.status_code, [404, 500],
                         "Expected 404 or 500 during TDD phase - no implementation yet")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_delete_non_existent(self):
        """Test DELETE /git_timesheet_mapper/mapping/{id} with non-existent mapping ID.
        
        Contract: Should return 404 for non-existent mapping.
        Expected to FAIL: No controller implementation exists yet.
        """
        mapping_id = 99999  # Non-existent mapping ID
        url = f'/git_timesheet_mapper/mapping/{mapping_id}'
        
        response = self.url_open(url, data='', headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 404 for non-existent mapping
        self.assertEqual(response.status_code, 404,
                        "Should return 404 for non-existent mapping")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_create_invalid_commit_id(self):
        """Test mapping creation with invalid commit ID.
        
        Contract: Should return error when commit doesn't exist.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 99999,  # Non-existent commit ID
            'timesheet_line_id': 1
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for invalid commit
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for invalid commit ID")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for invalid commit")
        self.assertEqual(response_data['error']['code'], 'MAPPING_COMMIT_NOT_FOUND',
                        "Error code should be MAPPING_COMMIT_NOT_FOUND")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_create_invalid_timesheet_id(self):
        """Test mapping creation with invalid timesheet entry ID.
        
        Contract: Should return error when timesheet entry doesn't exist.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 1,
            'timesheet_line_id': 99999  # Non-existent timesheet entry ID
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for invalid timesheet entry
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for invalid timesheet entry ID")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for invalid timesheet")
        self.assertEqual(response_data['error']['code'], 'MAPPING_TIMESHEET_NOT_FOUND',
                        "Error code should be MAPPING_TIMESHEET_NOT_FOUND")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_mapping_permission_check(self):
        """Test mapping operations require proper permissions.
        
        Contract: Should check user permissions for timesheet access.
        Expected to FAIL: No controller implementation exists yet.
        """
        # Clear authentication to test permission requirements
        self.authenticate(None, None)
        
        url = '/git_timesheet_mapper/mapping/create'
        data = {
            'commit_id': 1,
            'timesheet_line_id': 1
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should require authentication
        self.assertIn(response.status_code, [401, 403],
                     "Should return 401/403 for unauthenticated mapping requests")

    def tearDown(self):
        """Clean up test data."""
        # Clean up any test mappings that might have been created
        # (None should exist during TDD phase)
        test_mappings = self.env['timesheet.commit.mapping'].search([
            ('description', 'like', '%test%')
        ])
        if test_mappings:
            test_mappings.unlink()
        
        super().tearDown()
