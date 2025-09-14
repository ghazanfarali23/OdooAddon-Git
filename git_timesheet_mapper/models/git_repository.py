# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import requests
import re
from urllib.parse import urlparse


class GitRepository(models.Model):
    """Git Repository model for storing repository connection information.
    
    Supports both GitHub and GitLab repositories with authentication.
    Provides methods for testing connectivity and fetching repository data.
    """
    
    _name = 'git.repository'
    _description = 'Git Repository'
    _rec_name = 'name'
    _order = 'name asc'
    
    # Basic Information
    name = fields.Char(
        string='Repository Name',
        required=True,
        help='Display name for this repository'
    )
    
    repository_type = fields.Selection([
        ('github', 'GitHub'),
        ('gitlab', 'GitLab')
    ], string='Repository Type', required=True, default='github')
    
    repository_url = fields.Char(
        string='Repository URL',
        required=True,
        help='Full URL to the repository (e.g., https://github.com/owner/repo)'
    )
    
    # Authentication
    access_token = fields.Char(
        string='Access Token',
        help='Personal access token for private repositories'
    )
    
    is_private = fields.Boolean(
        string='Private Repository',
        default=False,
        help='Whether this repository requires authentication'
    )
    
    # Repository Details
    owner = fields.Char(
        string='Repository Owner',
        compute='_compute_repository_details',
        store=True,
        help='Repository owner/organization'
    )
    
    repo_name = fields.Char(
        string='Repository Name',
        compute='_compute_repository_details', 
        store=True,
        help='Repository name'
    )
    
    default_branch = fields.Char(
        string='Default Branch',
        default='main',
        help='Default branch to fetch commits from'
    )
    
    # Project Association
    project_id = fields.Many2one(
        'project.project',
        string='Associated Project',
        help='Odoo project this repository is associated with'
    )
    
    # Status and Metadata
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        help='When commits were last fetched from this repository'
    )
    
    connection_status = fields.Selection([
        ('not_tested', 'Not Tested'),
        ('connected', 'Connected'),
        ('failed', 'Connection Failed')
    ], string='Connection Status', default='not_tested')
    
    connection_error = fields.Text(
        string='Connection Error',
        help='Error message from last connection attempt'
    )
    
    # Statistics
    total_commits = fields.Integer(
        string='Total Commits',
        compute='_compute_commit_stats',
        help='Total number of commits fetched'
    )
    
    mapped_commits = fields.Integer(
        string='Mapped Commits',
        compute='_compute_commit_stats',
        help='Number of commits mapped to timesheets'
    )
    
    unmapped_commits = fields.Integer(
        string='Unmapped Commits',
        compute='_compute_commit_stats',
        help='Number of commits not yet mapped'
    )
    
    # Audit Trail
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_repository_company', 
         'UNIQUE(repository_url, company_id)',
         'Repository URL must be unique per company!')
    ]
    
    @api.depends('repository_url')
    def _compute_repository_details(self):
        """Extract owner and repository name from URL."""
        for record in self:
            if record.repository_url:
                try:
                    # Parse URL to extract owner and repo name
                    # Supports: https://github.com/owner/repo, https://gitlab.com/owner/repo
                    parsed_url = urlparse(record.repository_url)
                    path_parts = parsed_url.path.strip('/').split('/')
                    
                    if len(path_parts) >= 2:
                        record.owner = path_parts[0]
                        record.repo_name = path_parts[1].replace('.git', '')
                    else:
                        record.owner = False
                        record.repo_name = False
                except Exception:
                    record.owner = False
                    record.repo_name = False
            else:
                record.owner = False
                record.repo_name = False
    
    @api.depends('repository_url')
    def _compute_commit_stats(self):
        """Compute commit statistics."""
        for record in self:
            commits = self.env['git.commit'].search([
                ('repository_id', '=', record.id)
            ])
            
            record.total_commits = len(commits)
            record.mapped_commits = len(commits.filtered('is_mapped'))
            record.unmapped_commits = record.total_commits - record.mapped_commits
    
    @api.constrains('repository_url')
    def _check_repository_url(self):
        """Validate repository URL format."""
        for record in self:
            if record.repository_url:
                # Basic URL validation
                url_pattern = r'^https?://(github\.com|gitlab\.com)/[\w\-\.]+/[\w\-\.]+/?$'
                if not re.match(url_pattern, record.repository_url.rstrip('/')):
                    raise ValidationError(_(
                        'Invalid repository URL format. Expected format: '
                        'https://github.com/owner/repo or https://gitlab.com/owner/repo'
                    ))
    
    @api.constrains('access_token', 'is_private')
    def _check_private_access(self):
        """Validate that private repositories have access tokens."""
        for record in self:
            if record.is_private and not record.access_token:
                raise ValidationError(_(
                    'Private repositories require an access token.'
                ))
    
    def action_test_connection(self):
        """Test repository connection and update status.
        
        Returns:
            dict: Result with success status and message
        """
        self.ensure_one()
        
        try:
            if self.repository_type == 'github':
                result = self._test_github_connection()
            elif self.repository_type == 'gitlab':
                result = self._test_gitlab_connection()
            else:
                raise ValidationError(_('Unsupported repository type'))
                
            if result['success']:
                self.connection_status = 'connected'
                self.connection_error = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _('Connection successful!'),
                        'sticky': False,
                    }
                }
            else:
                self.connection_status = 'failed'
                self.connection_error = result.get('error', 'Unknown error')
                raise UserError(result.get('error', 'Connection failed'))
                
        except Exception as e:
            self.connection_status = 'failed'
            self.connection_error = str(e)
            raise UserError(_('Connection failed: %s') % str(e))
    
    def _test_github_connection(self):
        """Test GitHub repository connection.
        
        Returns:
            dict: Result with success status and optional error message
        """
        try:
            api_url = f'https://api.github.com/repos/{self.owner}/{self.repo_name}'
            headers = {}
            
            if self.access_token:
                headers['Authorization'] = f'token {self.access_token}'
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                # Update default branch if different
                if repo_data.get('default_branch') != self.default_branch:
                    self.default_branch = repo_data.get('default_branch', 'main')
                return {'success': True}
            elif response.status_code == 404:
                return {'success': False, 'error': 'Repository not found or not accessible'}
            elif response.status_code == 401:
                return {'success': False, 'error': 'Invalid access token'}
            else:
                return {'success': False, 'error': f'GitHub API error: {response.status_code}'}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Connection timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Network error: {str(e)}'}
    
    def _test_gitlab_connection(self):
        """Test GitLab repository connection.
        
        Returns:
            dict: Result with success status and optional error message
        """
        try:
            # Extract GitLab instance URL (gitlab.com or self-hosted)
            parsed_url = urlparse(self.repository_url)
            gitlab_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Encode project path for API
            project_path = f"{self.owner}/{self.repo_name}".replace('/', '%2F')
            api_url = f'{gitlab_host}/api/v4/projects/{project_path}'
            
            headers = {}
            if self.access_token:
                headers['Private-Token'] = self.access_token
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                # Update default branch if different  
                if repo_data.get('default_branch') != self.default_branch:
                    self.default_branch = repo_data.get('default_branch', 'main')
                return {'success': True}
            elif response.status_code == 404:
                return {'success': False, 'error': 'Repository not found or not accessible'}
            elif response.status_code == 401:
                return {'success': False, 'error': 'Invalid access token'}
            else:
                return {'success': False, 'error': f'GitLab API error: {response.status_code}'}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Connection timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Network error: {str(e)}'}
    
    def get_branches(self):
        """Get list of branches from repository.
        
        Returns:
            list: List of branch names
        """
        self.ensure_one()
        
        if self.repository_type == 'github':
            return self._get_github_branches()
        elif self.repository_type == 'gitlab':
            return self._get_gitlab_branches()
        else:
            raise ValidationError(_('Unsupported repository type'))
    
    def _get_github_branches(self):
        """Get branches from GitHub repository."""
        try:
            api_url = f'https://api.github.com/repos/{self.owner}/{self.repo_name}/branches'
            headers = {}
            
            if self.access_token:
                headers['Authorization'] = f'token {self.access_token}'
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                branches_data = response.json()
                return [branch['name'] for branch in branches_data]
            else:
                raise UserError(_('Failed to fetch branches: %s') % response.status_code)
                
        except requests.exceptions.RequestException as e:
            raise UserError(_('Network error fetching branches: %s') % str(e))
    
    def _get_gitlab_branches(self):
        """Get branches from GitLab repository."""
        try:
            parsed_url = urlparse(self.repository_url)
            gitlab_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
            project_path = f"{self.owner}/{self.repo_name}".replace('/', '%2F')
            api_url = f'{gitlab_host}/api/v4/projects/{project_path}/repository/branches'
            
            headers = {}
            if self.access_token:
                headers['Private-Token'] = self.access_token
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                branches_data = response.json()
                return [branch['name'] for branch in branches_data]
            else:
                raise UserError(_('Failed to fetch branches: %s') % response.status_code)
                
        except requests.exceptions.RequestException as e:
            raise UserError(_('Network error fetching branches: %s') % str(e))
    
    def action_fetch_commits(self):
        """Trigger commit fetch for this repository.
        
        Returns:
            dict: Action to show fetched commits
        """
        self.ensure_one()
        
        # Call commit fetching service
        commit_service = self.env['git.commit.service']
        result = commit_service.fetch_commits(self)
        
        if result['success']:
            self.last_sync_date = fields.Datetime.now()
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Fetched Commits'),
                'res_model': 'git.commit',
                'view_mode': 'tree,form',
                'domain': [('repository_id', '=', self.id)],
                'context': {'default_repository_id': self.id}
            }
        else:
            raise UserError(_('Failed to fetch commits: %s') % result.get('error'))
    
    def action_view_commits(self):
        """View commits for this repository."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Repository Commits'),
            'res_model': 'git.commit',
            'view_mode': 'tree,form',
            'domain': [('repository_id', '=', self.id)],
            'context': {
                'default_repository_id': self.id,
                'search_default_unmapped': 1
            }
        }
    
    def action_view_mappings(self):
        """View commit mappings for this repository."""
        self.ensure_one()
        
        commit_ids = self.env['git.commit'].search([
            ('repository_id', '=', self.id)
        ]).ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commit Mappings'),
            'res_model': 'timesheet.commit.mapping',
            'view_mode': 'tree,form',
            'domain': [('commit_id', 'in', commit_ids)],
            'context': {'default_repository_id': self.id}
        }
