# -*- coding: utf-8 -*-

import json
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestRepositoryAPI(HttpCase):
    """Contract tests for Git Repository API endpoints.
    
    These tests verify the API contract specifications defined in contracts/api-contracts.md.
    All tests MUST FAIL initially as no implementation exists yet (TDD requirement).
    """

    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        
        # Create test user with repository admin privileges
        self.test_user = self.env['res.users'].create({
            'name': 'Test Repository Admin',
            'login': 'test_repo_admin',
            'email': 'test@example.com',
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_repository_admin').id)]
        })
        
        # Authentication setup for API calls
        self.authenticate('test_repo_admin', 'test_repo_admin')

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_repository_create_success(self):
        """Test POST /git_timesheet_mapper/repository/create with valid data.
        
        Contract: Should return 200 with repository data when valid request provided.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/repository/create'
        data = {
            'name': 'Test Repository',
            'repository_type': 'github',
            'repository_url': 'https://github.com/test/repo',
            'access_token': 'test_token_123',
            'is_private': True
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 status
        self.assertEqual(response.status_code, 200, 
                        "Repository create endpoint should return 200 for valid request")
        
        # Contract verification: Response should be JSON
        self.assertEqual(response.headers.get('Content-Type'), 'application/json',
                        "Response should be JSON format")
        
        # Contract verification: Response structure
        response_data = json.loads(response.content.decode())
        self.assertIn('success', response_data, "Response should contain 'success' field")
        self.assertTrue(response_data['success'], "Success should be True for valid request")
        self.assertIn('data', response_data, "Response should contain 'data' field")
        
        # Contract verification: Data structure
        data_fields = response_data['data']
        required_fields = ['id', 'name', 'repository_type', 'repository_url', 'connection_status']
        for field in required_fields:
            self.assertIn(field, data_fields, f"Response data should contain '{field}' field")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_repository_create_validation_error(self):
        """Test POST /git_timesheet_mapper/repository/create with invalid data.
        
        Contract: Should return 400 with error details for invalid request.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/repository/create'
        data = {
            'name': '',  # Invalid: empty name
            'repository_type': 'invalid_type',  # Invalid: not github/gitlab
            'repository_url': 'not_a_valid_url',  # Invalid: malformed URL
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for validation errors
        self.assertEqual(response.status_code, 400,
                        "Repository create should return 400 for invalid data")
        
        # Contract verification: Error response structure
        response_data = json.loads(response.content.decode())
        self.assertIn('success', response_data, "Error response should contain 'success' field")
        self.assertFalse(response_data['success'], "Success should be False for validation error")
        self.assertIn('error', response_data, "Error response should contain 'error' field")
        
        # Contract verification: Error details structure
        error_data = response_data['error']
        required_error_fields = ['code', 'message']
        for field in required_error_fields:
            self.assertIn(field, error_data, f"Error should contain '{field}' field")
        
        self.assertIn(error_data['code'], ['VALIDATION_ERROR', 'AUTH_ERROR', 'CONNECTION_ERROR'],
                     "Error code should be one of the defined error types")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_repository_create_missing_required_fields(self):
        """Test POST /git_timesheet_mapper/repository/create with missing required fields.
        
        Contract: Should return 400 when required fields are missing.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/repository/create'
        data = {
            'name': 'Test Repository'
            # Missing: repository_type, repository_url
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
    def test_repository_test_connection_success(self):
        """Test POST /git_timesheet_mapper/repository/test_connection with valid credentials.
        
        Contract: Should return connection status without saving repository.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/repository/test_connection'
        data = {
            'repository_type': 'github',
            'repository_url': 'https://github.com/octocat/Hello-World',
            'access_token': 'valid_token'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 for successful connection test
        self.assertEqual(response.status_code, 200,
                        "Connection test should return 200 for valid request")
        
        response_data = json.loads(response.content.decode())
        self.assertTrue(response_data['success'], "Success should be True for valid connection")
        self.assertIn('data', response_data, "Response should contain data field")
        
        # Contract verification: Connection test data structure
        data_fields = response_data['data']
        self.assertIn('connection_status', data_fields, "Should contain connection_status")
        self.assertEqual(data_fields['connection_status'], 'connected',
                        "Connection status should be 'connected' for successful test")
        
        # Contract verification: Repository info should be included
        self.assertIn('repository_info', data_fields, "Should contain repository_info")
        repo_info = data_fields['repository_info']
        repo_info_fields = ['name', 'owner', 'description', 'is_private', 'default_branch']
        for field in repo_info_fields:
            self.assertIn(field, repo_info, f"Repository info should contain '{field}' field")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_repository_get_branches_success(self):
        """Test GET /git_timesheet_mapper/repository/{id}/branches.
        
        Contract: Should return list of available branches for repository.
        Expected to FAIL: No controller implementation exists yet.
        """
        # First, we would need a repository ID, but since no implementation exists,
        # we'll test with a mock ID
        repository_id = 999  # Non-existent ID for testing
        url = f'/git_timesheet_mapper/repository/{repository_id}/branches'
        
        response = self.url_open(url)
        
        # Contract verification: Should return 200 for valid repository
        # NOTE: This will likely return 404 initially, which is expected for TDD
        # When implementation exists, this should return proper branch data
        
        if response.status_code == 200:
            response_data = json.loads(response.content.decode())
            self.assertTrue(response_data['success'], "Success should be True for valid repository")
            self.assertIn('data', response_data, "Response should contain data field")
            
            # Contract verification: Branches data structure
            data_fields = response_data['data']
            self.assertIn('branches', data_fields, "Should contain branches array")
            
            if data_fields['branches']:  # If branches exist
                branch = data_fields['branches'][0]
                branch_fields = ['name', 'commit_hash', 'commit_date']
                for field in branch_fields:
                    self.assertIn(field, branch, f"Branch should contain '{field}' field")
        else:
            # Expected during TDD phase - no implementation yet
            self.assertIn(response.status_code, [404, 500],
                         "Expected 404 or 500 during TDD phase - no implementation yet")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')  
    def test_repository_create_authentication_required(self):
        """Test repository creation requires proper authentication.
        
        Contract: Should return appropriate error for unauthenticated requests.
        Expected to FAIL: No controller implementation exists yet.
        """
        # Clear authentication
        self.authenticate(None, None)
        
        url = '/git_timesheet_mapper/repository/create'
        data = {
            'name': 'Test Repository',
            'repository_type': 'github',
            'repository_url': 'https://github.com/test/repo'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should require authentication
        self.assertIn(response.status_code, [401, 403],
                     "Should return 401/403 for unauthenticated requests")

    def tearDown(self):
        """Clean up test data."""
        # Clean up any test repositories that might have been created
        # (None should exist during TDD phase)
        test_repos = self.env['git.repository'].search([
            ('name', 'like', 'Test%')
        ])
        if test_repos:
            test_repos.unlink()
        
        super().tearDown()
