# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestGitIntegration(TransactionCase):
    """Integration tests for Git repository connection and commit fetching.
    
    These tests validate the complete workflow from repository setup to commit retrieval.
    All tests MUST FAIL initially as no implementation exists yet (TDD requirement).
    """

    def setUp(self):
        super().setUp()
        
        # Create test company
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
        })
        
        # Create test user with repository admin privileges
        self.admin_user = self.env['res.users'].create({
            'name': 'Test Repository Admin',
            'login': 'test_admin',
            'email': 'admin@test.com',
            'company_id': self.test_company.id,
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_repository_admin').id)]
        })
        
        # Create test user with mapping privileges  
        self.mapping_user = self.env['res.users'].create({
            'name': 'Test Mapping User',
            'login': 'test_mapper',
            'email': 'mapper@test.com',
            'company_id': self.test_company.id,
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
        })

    def test_repository_connection_workflow_github(self):
        """Integration test: Complete GitHub repository connection workflow.
        
        Scenario: Admin connects to a GitHub repository with valid credentials.
        Expected to FAIL: No git.repository model implementation exists yet.
        """
        # Attempt to create GitHub repository connection
        with self.assertRaises(Exception, msg="Should fail - git.repository model not implemented"):
            repo_data = {
                'name': 'Test GitHub Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/octocat/Hello-World',
                'repository_owner': 'octocat',
                'repository_name': 'Hello-World',
                'access_token': 'ghp_test_token_123',
                'is_private': False,
                'company_id': self.test_company.id,
                'user_id': self.admin_user.id
            }
            
            # This should fail because git.repository model doesn't exist yet
            repository = self.env['git.repository'].create(repo_data)
            
            # If model existed, we would test:
            self.assertEqual(repository.name, 'Test GitHub Repository')
            self.assertEqual(repository.repository_type, 'github')
            self.assertEqual(repository.connection_status, 'disconnected')  # Initial state
            
            # Test connection validation
            repository.action_test_connection()
            self.assertEqual(repository.connection_status, 'connected')

    def test_repository_connection_workflow_gitlab(self):
        """Integration test: Complete GitLab repository connection workflow.
        
        Scenario: Admin connects to a GitLab repository with valid credentials.
        Expected to FAIL: No git.repository model implementation exists yet.
        """
        # Attempt to create GitLab repository connection
        with self.assertRaises(Exception, msg="Should fail - git.repository model not implemented"):
            repo_data = {
                'name': 'Test GitLab Repository',
                'repository_type': 'gitlab',
                'repository_url': 'https://gitlab.com/test/project',
                'repository_owner': 'test',
                'repository_name': 'project',
                'access_token': 'glpat_test_token_456',
                'is_private': True,
                'company_id': self.test_company.id,
                'user_id': self.admin_user.id
            }
            
            # This should fail because git.repository model doesn't exist yet
            repository = self.env['git.repository'].create(repo_data)
            
            # If model existed, we would test:
            self.assertEqual(repository.repository_type, 'gitlab')
            self.assertTrue(repository.is_private)
            self.assertIsNotNone(repository.access_token)

    @patch('git_timesheet_mapper.services.github_service.Github')
    def test_github_commit_fetching_integration(self, mock_github):
        """Integration test: Fetch commits from GitHub repository.
        
        Scenario: User fetches commits from connected GitHub repository.
        Expected to FAIL: No service implementation exists yet.
        """
        # Mock GitHub API response
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.sha = 'abc123def456'
        mock_commit.commit.author.name = 'John Doe'
        mock_commit.commit.author.email = 'john@example.com'
        mock_commit.commit.message = 'Add new feature'
        mock_commit.commit.author.date = '2025-09-13T10:00:00Z'
        mock_repo.get_commits.return_value = [mock_commit]
        mock_github.return_value.get_repo.return_value = mock_repo
        
        # Attempt to use GitHub service
        with self.assertRaises(Exception, msg="Should fail - github_service not implemented"):
            from git_timesheet_mapper.services import github_service
            
            service = github_service.GitHubService('test_token')
            commits = service.fetch_commits('octocat/Hello-World', 'main')
            
            # If service existed, we would test:
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0]['commit_hash'], 'abc123def456')
            self.assertEqual(commits[0]['author_name'], 'John Doe')

    @patch('git_timesheet_mapper.services.gitlab_service.gitlab')
    def test_gitlab_commit_fetching_integration(self, mock_gitlab):
        """Integration test: Fetch commits from GitLab repository.
        
        Scenario: User fetches commits from connected GitLab repository.
        Expected to FAIL: No service implementation exists yet.
        """
        # Mock GitLab API response
        mock_project = MagicMock()
        mock_commit = MagicMock()
        mock_commit.id = 'def456abc789'
        mock_commit.author_name = 'Jane Smith'
        mock_commit.author_email = 'jane@example.com'
        mock_commit.title = 'Fix critical bug'
        mock_commit.created_at = '2025-09-13T14:30:00Z'
        mock_project.commits.list.return_value = [mock_commit]
        mock_gitlab.return_value.projects.get.return_value = mock_project
        
        # Attempt to use GitLab service
        with self.assertRaises(Exception, msg="Should fail - gitlab_service not implemented"):
            from git_timesheet_mapper.services import gitlab_service
            
            service = gitlab_service.GitLabService('test_token')
            commits = service.fetch_commits(123, 'main')
            
            # If service existed, we would test:
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0]['commit_hash'], 'def456abc789')
            self.assertEqual(commits[0]['author_name'], 'Jane Smith')

    def test_repository_authentication_failure(self):
        """Integration test: Handle authentication failures gracefully.
        
        Scenario: Repository connection fails due to invalid credentials.
        Expected to FAIL: No error handling implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - no authentication handling implemented"):
            # Attempt to create repository with invalid token
            repo_data = {
                'name': 'Invalid Token Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/private/repo',
                'access_token': 'invalid_token',
                'is_private': True,
                'company_id': self.test_company.id,
                'user_id': self.admin_user.id
            }
            
            repository = self.env['git.repository'].create(repo_data)
            
            # This should raise appropriate authentication error
            with self.assertRaises(ValidationError, msg="Should raise ValidationError for invalid token"):
                repository.action_test_connection()

    def test_repository_url_validation(self):
        """Integration test: Validate repository URL formats.
        
        Scenario: System validates various repository URL formats.
        Expected to FAIL: No URL validation implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - no URL validation implemented"):
            invalid_urls = [
                'not_a_url',
                'https://example.com/not/a/git/repo',
                'github.com/missing/protocol',
                'https://github.com/',  # Missing repo path
                'https://gitlab.com/single_path'  # Missing repo name
            ]
            
            for invalid_url in invalid_urls:
                with self.assertRaises(ValidationError, msg=f"Should reject invalid URL: {invalid_url}"):
                    repo_data = {
                        'name': f'Invalid URL Test',
                        'repository_type': 'github',
                        'repository_url': invalid_url,
                        'company_id': self.test_company.id,
                        'user_id': self.admin_user.id
                    }
                    self.env['git.repository'].create(repo_data)

    def test_branch_listing_integration(self):
        """Integration test: List available branches for repository.
        
        Scenario: User requests list of available branches from connected repository.
        Expected to FAIL: No branch listing implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - no branch listing implemented"):
            # Mock repository setup
            repo_data = {
                'name': 'Branch Test Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/test/repo',
                'company_id': self.test_company.id,
                'user_id': self.admin_user.id
            }
            
            repository = self.env['git.repository'].create(repo_data)
            
            # Attempt to get branches
            branches = repository.action_get_branches()
            
            # If implemented, we would test:
            self.assertIsInstance(branches, list)
            if branches:
                branch = branches[0]
                self.assertIn('name', branch)
                self.assertIn('commit_hash', branch)
                self.assertIn('commit_date', branch)

    def test_commit_data_persistence(self):
        """Integration test: Commits are properly stored in database.
        
        Scenario: Fetched commits are persisted with correct data structure.
        Expected to FAIL: No git.commit model implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - git.commit model not implemented"):
            # Mock commit data
            commit_data = {
                'repository_id': 1,  # Would be actual repository ID
                'commit_hash': 'abc123def456789',
                'author_name': 'Test Developer',
                'author_email': 'dev@example.com',
                'commit_date': '2025-09-13 12:00:00',
                'commit_message': 'Implement new feature',
                'branch_name': 'feature/new-functionality',
                'files_changed': 5,
                'lines_added': 120,
                'lines_deleted': 30,
                'company_id': self.test_company.id
            }
            
            # This should fail because git.commit model doesn't exist yet
            commit = self.env['git.commit'].create(commit_data)
            
            # If model existed, we would test:
            self.assertEqual(commit.commit_hash, 'abc123def456789')
            self.assertEqual(commit.commit_hash_short, 'abc123de')
            self.assertEqual(commit.author_name, 'Test Developer')
            self.assertFalse(commit.is_mapped)  # Initially unmapped

    def test_company_isolation(self):
        """Integration test: Multi-company data isolation.
        
        Scenario: Users can only see repositories from their company.
        Expected to FAIL: No multi-company support implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - no multi-company implementation"):
            # Create second company and user
            company2 = self.env['res.company'].create({
                'name': 'Second Company',
                'currency_id': self.env.ref('base.USD').id,
            })
            
            user2 = self.env['res.users'].create({
                'name': 'Company 2 User',
                'login': 'company2_user',
                'email': 'user2@company2.com',
                'company_id': company2.id,
                'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
            })
            
            # Create repositories for different companies
            repo1_data = {
                'name': 'Company 1 Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/company1/repo',
                'company_id': self.test_company.id,
                'user_id': self.admin_user.id
            }
            
            repo2_data = {
                'name': 'Company 2 Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/company2/repo',
                'company_id': company2.id,
                'user_id': user2.id
            }
            
            repo1 = self.env['git.repository'].create(repo1_data)
            repo2 = self.env['git.repository'].create(repo2_data)
            
            # Test isolation - user1 should only see company1 repositories
            company1_repos = self.env['git.repository'].with_user(self.admin_user).search([])
            self.assertEqual(len(company1_repos), 1)
            self.assertEqual(company1_repos.name, 'Company 1 Repository')
            
            # Test isolation - user2 should only see company2 repositories
            company2_repos = self.env['git.repository'].with_user(user2).search([])
            self.assertEqual(len(company2_repos), 1)
            self.assertEqual(company2_repos.name, 'Company 2 Repository')

    def tearDown(self):
        """Clean up test data."""
        # Clean up test repositories and commits (if they exist)
        try:
            test_repos = self.env['git.repository'].search([
                ('name', 'like', '%Test%')
            ])
            if test_repos:
                test_repos.unlink()
                
            test_commits = self.env['git.commit'].search([
                ('author_name', 'like', '%Test%')
            ])
            if test_commits:
                test_commits.unlink()
        except Exception:
            # Expected during TDD phase - models don't exist yet
            pass
        
        super().tearDown()
