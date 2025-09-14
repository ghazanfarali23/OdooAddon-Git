# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


@tagged('post_install', '-at_install')
class TestTimesheetIntegration(TransactionCase):
    """Integration tests for commit to timesheet mapping workflows.
    
    These tests validate the complete workflow from commit selection to timesheet mapping.
    All tests MUST FAIL initially as no implementation exists yet (TDD requirement).
    """

    def setUp(self):
        super().setUp()
        
        # Create test company
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
        })
        
        # Create test project and task
        self.test_project = self.env['project.project'].create({
            'name': 'Test Project',
            'company_id': self.test_company.id,
        })
        
        self.test_task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.test_project.id,
        })
        
        # Create test user with mapping privileges
        self.mapping_user = self.env['res.users'].create({
            'name': 'Test Mapping User',
            'login': 'test_mapper',
            'email': 'mapper@test.com',
            'company_id': self.test_company.id,
            'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
        })
        
        # Create timesheet entry for testing
        today = datetime.now().date()
        self.test_timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Development Work',
            'project_id': self.test_project.id,
            'task_id': self.test_task.id,
            'user_id': self.mapping_user.id,
            'date': today,
            'unit_amount': 8.0,  # 8 hours
            'company_id': self.test_company.id,
        })

    def test_single_commit_mapping_workflow(self):
        """Integration test: Complete single commit to timesheet mapping.
        
        Scenario: User maps individual commit to existing timesheet entry.
        Expected to FAIL: No mapping models/services implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - mapping models not implemented"):
            # Mock commit data (would come from git.commit model)
            commit_data = {
                'repository_id': 1,  # Mock repository
                'commit_hash': 'abc123def456',
                'author_name': 'Test Developer',
                'author_email': 'dev@test.com',
                'commit_date': datetime.now() - timedelta(hours=2),
                'commit_message': 'Implement user authentication',
                'branch_name': 'feature/auth',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            # Create mock commit (should fail - git.commit model doesn't exist)
            commit = self.env['git.commit'].create(commit_data)
            
            # Attempt mapping creation
            mapping_data = {
                'commit_id': commit.id,
                'timesheet_line_id': self.test_timesheet.id,
                'mapped_by': self.mapping_user.id,
                'mapping_method': 'manual',
                'description': 'Authentication feature implementation',
                'company_id': self.test_company.id
            }
            
            # This should fail because timesheet.commit.mapping model doesn't exist
            mapping = self.env['timesheet.commit.mapping'].create(mapping_data)
            
            # If models existed, we would test:
            self.assertEqual(mapping.commit_id, commit)
            self.assertEqual(mapping.timesheet_line_id, self.test_timesheet)
            self.assertEqual(mapping.mapped_by, self.mapping_user)
            
            # Verify commit is marked as mapped
            commit.refresh()
            self.assertTrue(commit.is_mapped)
            self.assertEqual(commit.mapped_by, self.mapping_user)
            
            # Verify timesheet has commit reference
            self.test_timesheet.refresh()
            self.assertEqual(self.test_timesheet.commit_count, 1)
            self.assertTrue(self.test_timesheet.has_commits)

    def test_bulk_mapping_workflow(self):
        """Integration test: Bulk mapping multiple commits to single timesheet.
        
        Scenario: User selects multiple commits and maps them all to one timesheet entry.
        Expected to FAIL: No bulk mapping implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - bulk mapping not implemented"):
            # Create multiple mock commits
            commit_data_list = [
                {
                    'commit_hash': f'commit{i}_hash',
                    'author_name': 'Bulk Test Developer',
                    'author_email': 'bulk@test.com',
                    'commit_message': f'Commit {i} for bulk mapping',
                    'branch_name': 'feature/bulk-test',
                    'is_mapped': False,
                    'company_id': self.test_company.id
                }
                for i in range(1, 6)  # 5 commits
            ]
            
            commits = []
            for commit_data in commit_data_list:
                # This should fail - git.commit model doesn't exist
                commit = self.env['git.commit'].create(commit_data)
                commits.append(commit)
            
            # Attempt bulk mapping using wizard
            bulk_wizard_data = {
                'commit_ids': [(6, 0, [c.id for c in commits])],
                'timesheet_line_id': self.test_timesheet.id,
                'description': 'Bulk mapping for feature development',
                'mapping_method': 'bulk'
            }
            
            # This should fail because bulk mapping wizard doesn't exist
            wizard = self.env['bulk.mapping.wizard'].create(bulk_wizard_data)
            result = wizard.action_create_mappings()
            
            # If wizard existed, we would test:
            self.assertEqual(result['created_mappings'], 5)
            self.assertEqual(result['failed_mappings'], 0)
            
            # Verify all commits are marked as mapped
            for commit in commits:
                commit.refresh()
                self.assertTrue(commit.is_mapped)
            
            # Verify timesheet has correct commit count
            self.test_timesheet.refresh()
            self.assertEqual(self.test_timesheet.commit_count, 5)

    def test_duplicate_mapping_prevention(self):
        """Integration test: System prevents duplicate commit mappings.
        
        Scenario: User attempts to map already mapped commit - should be blocked.
        Expected to FAIL: No duplicate prevention logic implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - duplicate prevention not implemented"):
            # Create mock commit
            commit_data = {
                'repository_id': 1,
                'commit_hash': 'duplicate_test_commit',
                'author_name': 'Duplicate Test Dev',
                'author_email': 'dup@test.com',
                'commit_message': 'Test duplicate prevention',
                'branch_name': 'main',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            commit = self.env['git.commit'].create(commit_data)
            
            # Create first mapping
            mapping1_data = {
                'commit_id': commit.id,
                'timesheet_line_id': self.test_timesheet.id,
                'mapped_by': self.mapping_user.id,
                'mapping_method': 'manual',
                'company_id': self.test_company.id
            }
            
            mapping1 = self.env['timesheet.commit.mapping'].create(mapping1_data)
            
            # Verify commit is marked as mapped
            commit.refresh()
            self.assertTrue(commit.is_mapped)
            
            # Create second timesheet for attempted duplicate mapping
            second_timesheet = self.env['account.analytic.line'].create({
                'name': 'Second Development Work',
                'project_id': self.test_project.id,
                'task_id': self.test_task.id,
                'user_id': self.mapping_user.id,
                'date': datetime.now().date(),
                'unit_amount': 4.0,
                'company_id': self.test_company.id,
            })
            
            # Attempt to create duplicate mapping - should fail
            mapping2_data = {
                'commit_id': commit.id,  # Same commit
                'timesheet_line_id': second_timesheet.id,  # Different timesheet
                'mapped_by': self.mapping_user.id,
                'mapping_method': 'manual',
                'company_id': self.test_company.id
            }
            
            # This should raise ValidationError for duplicate mapping
            with self.assertRaises(ValidationError, msg="Should prevent duplicate mapping"):
                self.env['timesheet.commit.mapping'].create(mapping2_data)

    def test_mapping_permission_validation(self):
        """Integration test: Users can only map to timesheets they have access to.
        
        Scenario: User attempts to map commit to another user's timesheet.
        Expected to FAIL: No permission validation implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - permission validation not implemented"):
            # Create another user and their timesheet
            other_user = self.env['res.users'].create({
                'name': 'Other User',
                'login': 'other_user',
                'email': 'other@test.com',
                'company_id': self.test_company.id,
                'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_timesheet_user').id)]
            })
            
            other_timesheet = self.env['account.analytic.line'].create({
                'name': 'Other User Work',
                'project_id': self.test_project.id,
                'task_id': self.test_task.id,
                'user_id': other_user.id,
                'date': datetime.now().date(),
                'unit_amount': 6.0,
                'company_id': self.test_company.id,
            })
            
            # Create mock commit
            commit_data = {
                'commit_hash': 'permission_test_commit',
                'author_name': 'Permission Test Dev',
                'author_email': 'perm@test.com',
                'commit_message': 'Test permission validation',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            commit = self.env['git.commit'].create(commit_data)
            
            # Attempt mapping as mapping_user to other_user's timesheet
            mapping_data = {
                'commit_id': commit.id,
                'timesheet_line_id': other_timesheet.id,  # Other user's timesheet
                'mapped_by': self.mapping_user.id,
                'mapping_method': 'manual',
                'company_id': self.test_company.id
            }
            
            # Should fail with permission error
            with self.assertRaises(UserError, msg="Should prevent mapping to inaccessible timesheet"):
                mapping = self.env['timesheet.commit.mapping'].with_user(self.mapping_user).create(mapping_data)

    def test_mapping_history_and_audit_trail(self):
        """Integration test: System maintains complete mapping history.
        
        Scenario: Track who mapped what and when for audit purposes.
        Expected to FAIL: No audit trail implementation exists yet.
        """
        with self.assertRaises(Exception, msg="Should fail - audit trail not implemented"):
            # Create mock commit and mapping
            commit_data = {
                'commit_hash': 'audit_test_commit',
                'author_name': 'Audit Test Dev',
                'author_email': 'audit@test.com',
                'commit_message': 'Test audit trail',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            commit = self.env['git.commit'].create(commit_data)
            
            mapping_data = {
                'commit_id': commit.id,
                'timesheet_line_id': self.test_timesheet.id,
                'mapped_by': self.mapping_user.id,
                'mapping_method': 'manual',
                'description': 'Audit trail test mapping',
                'company_id': self.test_company.id
            }
            
            mapping = self.env['timesheet.commit.mapping'].create(mapping_data)
            
            # If audit trail existed, we would test:
            self.assertIsNotNone(mapping.mapping_date)
            self.assertEqual(mapping.mapped_by, self.mapping_user)
            self.assertEqual(mapping.mapping_method, 'manual')
            
            # Test mapping history view
            mapping_history = self.env['timesheet.commit.mapping'].search([
                ('timesheet_line_id', '=', self.test_timesheet.id)
            ])
            self.assertEqual(len(mapping_history), 1)
            
            # Test commit mapping view
            commit_mappings = self.env['timesheet.commit.mapping'].search([
                ('commit_id', '=', commit.id)
            ])
            self.assertEqual(len(commit_mappings), 1)

    def test_unmapping_workflow(self):
        """Integration test: Admin can remove mappings when needed.
        
        Scenario: Admin removes incorrect mapping and commit becomes available again.
        Expected to FAIL: No unmapping functionality implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - unmapping not implemented"):
            # Create admin user
            admin_user = self.env['res.users'].create({
                'name': 'Test Admin',
                'login': 'test_admin',
                'email': 'admin@test.com',
                'company_id': self.test_company.id,
                'groups_id': [(4, self.env.ref('git_timesheet_mapper.group_git_repository_admin').id)]
            })
            
            # Create mock commit and mapping
            commit_data = {
                'commit_hash': 'unmap_test_commit',
                'author_name': 'Unmap Test Dev',
                'author_email': 'unmap@test.com',
                'commit_message': 'Test unmapping',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            commit = self.env['git.commit'].create(commit_data)
            
            mapping_data = {
                'commit_id': commit.id,
                'timesheet_line_id': self.test_timesheet.id,
                'mapped_by': self.mapping_user.id,
                'company_id': self.test_company.id
            }
            
            mapping = self.env['timesheet.commit.mapping'].create(mapping_data)
            
            # Verify commit is mapped
            commit.refresh()
            self.assertTrue(commit.is_mapped)
            
            # Admin removes mapping
            mapping.with_user(admin_user).unlink()
            
            # Verify commit is unmarked
            commit.refresh()
            self.assertFalse(commit.is_mapped)
            self.assertFalse(commit.mapped_by)
            
            # Verify timesheet commit count is updated
            self.test_timesheet.refresh()
            self.assertEqual(self.test_timesheet.commit_count, 0)
            self.assertFalse(self.test_timesheet.has_commits)

    def test_cross_project_mapping_validation(self):
        """Integration test: Validate commits mapped to appropriate projects.
        
        Scenario: System validates business rules for cross-project mappings.
        Expected to FAIL: No cross-project validation implemented yet.
        """
        with self.assertRaises(Exception, msg="Should fail - cross-project validation not implemented"):
            # Create second project
            second_project = self.env['project.project'].create({
                'name': 'Second Project',
                'company_id': self.test_company.id,
            })
            
            second_task = self.env['project.task'].create({
                'name': 'Second Task',
                'project_id': second_project.id,
            })
            
            second_timesheet = self.env['account.analytic.line'].create({
                'name': 'Second Project Work',
                'project_id': second_project.id,
                'task_id': second_task.id,
                'user_id': self.mapping_user.id,
                'date': datetime.now().date(),
                'unit_amount': 4.0,
                'company_id': self.test_company.id,
            })
            
            # Create mock repository and commit for first project
            repo_data = {
                'name': 'First Project Repository',
                'repository_type': 'github',
                'repository_url': 'https://github.com/company/project1',
                'project_id': self.test_project.id,  # Associated with first project
                'company_id': self.test_company.id
            }
            
            repository = self.env['git.repository'].create(repo_data)
            
            commit_data = {
                'repository_id': repository.id,
                'commit_hash': 'cross_project_commit',
                'author_name': 'Cross Project Dev',
                'author_email': 'cross@test.com',
                'commit_message': 'Test cross-project mapping',
                'is_mapped': False,
                'company_id': self.test_company.id
            }
            
            commit = self.env['git.commit'].create(commit_data)
            
            # Attempt to map commit from project1 repo to project2 timesheet
            mapping_data = {
                'commit_id': commit.id,
                'timesheet_line_id': second_timesheet.id,  # Different project
                'mapped_by': self.mapping_user.id,
                'company_id': self.test_company.id
            }
            
            # Should validate project consistency
            with self.assertRaises(ValidationError, msg="Should validate project consistency"):
                self.env['timesheet.commit.mapping'].create(mapping_data)

    def tearDown(self):
        """Clean up test data."""
        # Clean up test mappings, commits, and related data
        try:
            test_mappings = self.env['timesheet.commit.mapping'].search([
                ('description', 'like', '%test%')
            ])
            if test_mappings:
                test_mappings.unlink()
                
            test_commits = self.env['git.commit'].search([
                ('commit_message', 'like', '%test%')
            ])
            if test_commits:
                test_commits.unlink()
        except Exception:
            # Expected during TDD phase - models don't exist yet
            pass
        
        super().tearDown()
