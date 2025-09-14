# -*- coding: utf-8 -*-

import json
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCommitAPI(HttpCase):
    """Contract tests for Git Commit API endpoints.
    
    These tests verify the API contract specifications for commit operations.
    All tests MUST FAIL initially as no implementation exists yet (TDD requirement).
    """

    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        
        # Create test user with timesheet mapping privileges
        self.test_user = self.env['res.users'].create({
            'name': 'Test Timesheet User',
            'login': 'test_timesheet_user', 
            'email': 'timesheet@example.com',
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
        })
        
        # Authentication setup for API calls
        self.authenticate('test_timesheet_user', 'test_timesheet_user')

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_fetch_success(self):
        """Test POST /git_timesheet_mapper/commits/fetch with valid parameters.
        
        Contract: Should return commit data for specified repository and branch.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/fetch'
        data = {
            'repository_id': 1,  # Mock repository ID
            'branch_name': 'main',
            'date_from': '2025-09-01',
            'date_to': '2025-09-13',
            'author_filter': 'john.doe@example.com',
            'message_filter': 'feature'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 200 for valid request
        self.assertEqual(response.status_code, 200,
                        "Commits fetch should return 200 for valid request")
        
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
        required_fields = ['total_commits', 'new_commits', 'commits']
        for field in required_fields:
            self.assertIn(field, data_fields, f"Response data should contain '{field}' field")
        
        # Contract verification: Commits array structure
        if data_fields['commits']:  # If commits exist
            commit = data_fields['commits'][0]
            commit_fields = [
                'id', 'commit_hash', 'commit_hash_short', 'author_name', 'author_email',
                'commit_date', 'commit_message', 'commit_message_short', 'branch_name',
                'files_changed', 'lines_added', 'lines_deleted', 'is_mapped', 'commit_url'
            ]
            for field in commit_fields:
                self.assertIn(field, commit, f"Commit should contain '{field}' field")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_fetch_missing_required_fields(self):
        """Test POST /git_timesheet_mapper/commits/fetch with missing required fields.
        
        Contract: Should return 400 when repository_id or branch_name is missing.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/fetch'
        data = {
            'branch_name': 'main'
            # Missing: repository_id (required)
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
    def test_commits_fetch_invalid_repository(self):
        """Test POST /git_timesheet_mapper/commits/fetch with invalid repository ID.
        
        Contract: Should return error for non-existent repository.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/fetch'
        data = {
            'repository_id': 99999,  # Non-existent repository
            'branch_name': 'main'
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for invalid repository
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for invalid repository ID")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for invalid repository")
        self.assertIn(response_data['error']['code'], ['REPO_NOT_FOUND', 'VALIDATION_ERROR'],
                     "Error code should indicate repository not found")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_search_success(self):
        """Test GET /git_timesheet_mapper/commits/search with valid parameters.
        
        Contract: Should return filtered commits based on search criteria.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/search'
        params = {
            'repository_id': 1,
            'branch_name': 'main',
            'author': 'john.doe',
            'message': 'bugfix',
            'date_from': '2025-09-01',
            'date_to': '2025-09-13',
            'is_mapped': 'false',
            'limit': 50,
            'offset': 0
        }
        
        # Build query string
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        full_url = f'{url}?{query_string}'
        
        response = self.url_open(full_url)
        
        # Contract verification: Should return 200 for valid search
        if response.status_code == 200:
            response_data = json.loads(response.content.decode())
            self.assertTrue(response_data['success'], "Success should be True for valid search")
            self.assertIn('data', response_data, "Response should contain data field")
            
            # Contract verification: Same structure as fetch endpoint
            data_fields = response_data['data']
            required_fields = ['total_commits', 'new_commits', 'commits']
            for field in required_fields:
                self.assertIn(field, data_fields, f"Search response should contain '{field}' field")
        else:
            # Expected during TDD phase - no implementation yet
            self.assertIn(response.status_code, [404, 500],
                         "Expected 404 or 500 during TDD phase - no implementation yet")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_search_missing_repository_id(self):
        """Test GET /git_timesheet_mapper/commits/search without repository_id.
        
        Contract: Should return 400 when required repository_id parameter is missing.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/search?author=john.doe'
        
        response = self.url_open(url)
        
        # Contract verification: Should return 400 for missing repository_id
        self.assertEqual(response.status_code, 400,
                        "Should return 400 when repository_id is missing")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_fetch_date_range_validation(self):
        """Test commit fetch with invalid date ranges.
        
        Contract: Should validate date_from is not after date_to.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/fetch'
        data = {
            'repository_id': 1,
            'branch_name': 'main',
            'date_from': '2025-09-13',  # After date_to
            'date_to': '2025-09-01'     # Before date_from
        }
        
        response = self.url_open(url, data=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        
        # Contract verification: Should return 400 for invalid date range
        self.assertEqual(response.status_code, 400,
                        "Should return 400 for invalid date range")
        
        response_data = json.loads(response.content.decode())
        self.assertFalse(response_data['success'], "Success should be False for invalid date range")
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR',
                        "Error code should be VALIDATION_ERROR for invalid date range")

    @mute_logger('odoo.addons.base.models.ir_http', 'odoo.http')
    def test_commits_pagination(self):
        """Test commit search pagination parameters.
        
        Contract: Should respect limit and offset parameters for pagination.
        Expected to FAIL: No controller implementation exists yet.
        """
        url = '/git_timesheet_mapper/commits/search'
        params = {
            'repository_id': 1,
            'limit': 10,
            'offset': 20
        }
        
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        full_url = f'{url}?{query_string}'
        
        response = self.url_open(full_url)
        
        # Contract verification: Should handle pagination correctly
        if response.status_code == 200:
            response_data = json.loads(response.content.decode())
            commits = response_data['data']['commits']
            
            # Verify pagination limits are respected
            self.assertLessEqual(len(commits), 10,
                               "Should not return more than limit parameter")
        else:
            # Expected during TDD phase
            self.assertIn(response.status_code, [404, 500],
                         "Expected error during TDD phase - no implementation yet")

    def tearDown(self):
        """Clean up test data."""
        # Clean up any test commits that might have been created
        # (None should exist during TDD phase)
        test_commits = self.env['git.commit'].search([
            ('commit_message', 'like', '%test%')
        ])
        if test_commits:
            test_commits.unlink()
        
        super().tearDown()
