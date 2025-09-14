# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse, quote
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GitLabService(models.TransientModel):
    """GitLab API service for repository operations.
    
    Provides methods for connecting to GitLab repositories (GitLab.com or self-hosted),
    fetching commits, branches, and other repository data.
    Uses GitLab REST API v4 with authentication support.
    """
    
    _name = 'gitlab.service'
    _description = 'GitLab API Service'
    
    def __init__(self, pool, cr):
        """Initialize GitLab service."""
        super().__init__(pool, cr)
        self.session = None
    
    def _get_session(self, access_token=None):
        """Get configured requests session with authentication.
        
        Args:
            access_token: GitLab personal access token
            
        Returns:
            requests.Session: Configured session
        """
        if not self.session:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Odoo-Git-Timesheet-Mapper/1.0'
            })
        
        if access_token:
            self.session.headers['Private-Token'] = access_token
        elif 'Private-Token' in self.session.headers:
            # Remove old token if no new token provided
            del self.session.headers['Private-Token']
        
        return self.session
    
    def _get_gitlab_base_url(self, repository_url):
        """Extract GitLab instance base URL from repository URL.
        
        Args:
            repository_url: Full repository URL
            
        Returns:
            str: Base URL for GitLab API (e.g., https://gitlab.com/api/v4)
        """
        parsed_url = urlparse(repository_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return f"{base_url}/api/v4"
    
    def _make_request(self, method, url, repository_url=None, access_token=None, **kwargs):
        """Make authenticated request to GitLab API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or path relative to API base
            repository_url: Repository URL to determine GitLab instance
            access_token: Optional access token
            **kwargs: Additional arguments for requests
            
        Returns:
            dict: JSON response data
            
        Raises:
            UserError: For API errors or network issues
        """
        if not url.startswith('http') and repository_url:
            base_url = self._get_gitlab_base_url(repository_url)
            url = f"{base_url}/{url.lstrip('/')}"
        
        session = self._get_session(access_token)
        
        try:
            response = session.request(method, url, timeout=30, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 'unknown')
                raise UserError(_(
                    'GitLab API rate limit exceeded. Please wait %s seconds and try again.'
                ) % retry_after)
            
            # Handle authentication errors
            if response.status_code == 401:
                raise UserError(_('GitLab authentication failed. Please check your access token.'))
            
            # Handle forbidden access
            if response.status_code == 403:
                raise UserError(_('Access forbidden. Please check your permissions for this GitLab repository.'))
            
            # Handle not found
            if response.status_code == 404:
                raise UserError(_('GitLab repository not found or not accessible.'))
            
            # Handle other client errors
            if 400 <= response.status_code < 500:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', 'Unknown client error')
                except:
                    error_msg = f'HTTP {response.status_code} error'
                raise UserError(_('GitLab API error: %s') % error_msg)
            
            # Handle server errors
            if response.status_code >= 500:
                raise UserError(_('GitLab server error. Please try again later.'))
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise UserError(_('GitLab API request timed out. Please check your connection.'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Unable to connect to GitLab API. Please check your internet connection.'))
        except requests.exceptions.RequestException as e:
            raise UserError(_('GitLab API request failed: %s') % str(e))
    
    def test_connection(self, repository_url, access_token=None):
        """Test connection to GitLab repository.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token for private repos
            
        Returns:
            dict: Connection test result with success status and details
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Get project information
            project_data = self._make_request(
                'GET', 
                f'projects/{encoded_path}',
                repository_url=repository_url,
                access_token=access_token
            )
            
            return {
                'success': True,
                'repository': {
                    'name': project_data['name'],
                    'path_with_namespace': project_data['path_with_namespace'],
                    'description': project_data.get('description', ''),
                    'visibility': project_data.get('visibility', 'private'),
                    'default_branch': project_data.get('default_branch', 'main'),
                    'topics': project_data.get('topics', []),
                    'stars': project_data.get('star_count', 0),
                    'forks': project_data.get('forks_count', 0),
                    'created_at': project_data['created_at'],
                    'last_activity_at': project_data.get('last_activity_at', ''),
                    'web_url': project_data['web_url']
                }
            }
            
        except Exception as e:
            _logger.error(f"GitLab connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_branches(self, repository_url, access_token=None):
        """Get list of branches from GitLab repository.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            list: List of branch dictionaries with name and commit info
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Get branches with pagination support
            branches = []
            page = 1
            per_page = 100
            
            while True:
                branch_data = self._make_request(
                    'GET',
                    f'projects/{encoded_path}/repository/branches',
                    repository_url=repository_url,
                    access_token=access_token,
                    params={'page': page, 'per_page': per_page}
                )
                
                if not branch_data:
                    break
                
                for branch in branch_data:
                    branches.append({
                        'name': branch['name'],
                        'commit_sha': branch['commit']['id'],
                        'protected': branch.get('protected', False),
                        'merged': branch.get('merged', False),
                        'default': branch.get('default', False)
                    })
                
                # Check if we have more pages
                if len(branch_data) < per_page:
                    break
                
                page += 1
            
            return branches
            
        except Exception as e:
            _logger.error(f"Failed to fetch GitLab branches: {str(e)}")
            raise UserError(_('Failed to fetch branches: %s') % str(e))
    
    def fetch_commits(self, repository_url, access_token=None, branch='main', 
                     since=None, until=None, author=None, limit=100):
        """Fetch commits from GitLab repository.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            branch: Branch name to fetch commits from
            since: ISO 8601 date string to fetch commits since
            until: ISO 8601 date string to fetch commits until
            author: Filter commits by author
            limit: Maximum number of commits to fetch
            
        Returns:
            list: List of commit dictionaries
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Build parameters for commit fetching
            params = {
                'ref_name': branch,
                'per_page': min(limit, 100)  # GitLab max per page is 100
            }
            
            if since:
                params['since'] = since
            if until:
                params['until'] = until
            if author:
                params['author'] = author
            
            commits = []
            page = 1
            
            while len(commits) < limit:
                params['page'] = page
                
                commit_data = self._make_request(
                    'GET',
                    f'projects/{encoded_path}/repository/commits',
                    repository_url=repository_url,
                    access_token=access_token,
                    params=params
                )
                
                if not commit_data:
                    break
                
                for commit in commit_data:
                    if len(commits) >= limit:
                        break
                    
                    # Get detailed commit information
                    detailed_commit = self._get_commit_details(
                        repository_url, encoded_path, commit['id'], access_token
                    )
                    
                    commits.append(detailed_commit)
                
                # Check if we have more pages
                if len(commit_data) < params['per_page']:
                    break
                
                page += 1
            
            return commits[:limit]
            
        except Exception as e:
            _logger.error(f"Failed to fetch GitLab commits: {str(e)}")
            raise UserError(_('Failed to fetch commits: %s') % str(e))
    
    def _get_commit_details(self, repository_url, encoded_project_path, commit_sha, access_token=None):
        """Get detailed information for a specific commit.
        
        Args:
            repository_url: Full repository URL
            encoded_project_path: URL-encoded project path
            commit_sha: Commit SHA hash
            access_token: Optional access token
            
        Returns:
            dict: Detailed commit information
        """
        try:
            # Get commit details
            commit_data = self._make_request(
                'GET',
                f'projects/{encoded_project_path}/repository/commits/{commit_sha}',
                repository_url=repository_url,
                access_token=access_token
            )
            
            # Get commit statistics (diff stats)
            try:
                stats_data = self._make_request(
                    'GET',
                    f'projects/{encoded_project_path}/repository/commits/{commit_sha}/diff',
                    repository_url=repository_url,
                    access_token=access_token
                )
                
                # Calculate statistics from diff
                total_additions = 0
                total_deletions = 0
                files_changed = len(stats_data)
                
                for diff in stats_data:
                    # GitLab doesn't provide line counts directly in diff endpoint
                    # We would need to parse the actual diff content
                    # For now, we'll use basic file count
                    pass
                
            except Exception:
                # If stats fetch fails, use default values
                total_additions = 0
                total_deletions = 0
                files_changed = 0
            
            # Parse GitLab repository URL for web URL construction
            parsed_url = urlparse(repository_url)
            project_path = self._get_project_path(repository_url)
            web_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{project_path}/-/commit/{commit_sha}"
            
            return {
                'sha': commit_data['id'],
                'message': commit_data['message'],
                'author': {
                    'name': commit_data['author_name'],
                    'email': commit_data['author_email'],
                    'date': commit_data['authored_date']
                },
                'committer': {
                    'name': commit_data['committer_name'],
                    'email': commit_data['committer_email'],
                    'date': commit_data['committed_date']
                },
                'stats': {
                    'total': total_additions + total_deletions,
                    'additions': total_additions,
                    'deletions': total_deletions
                },
                'files': files_changed,
                'url': web_url,
                'api_url': f"{self._get_gitlab_base_url(repository_url)}/projects/{encoded_project_path}/repository/commits/{commit_sha}"
            }
            
        except Exception as e:
            _logger.warning(f"Failed to get detailed commit info for {commit_sha}: {str(e)}")
            # Return basic info if detailed fetch fails
            project_path = self._get_project_path(repository_url)
            parsed_url = urlparse(repository_url)
            web_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{project_path}/-/commit/{commit_sha}"
            
            return {
                'sha': commit_sha,
                'message': 'Unable to fetch detailed information',
                'author': {'name': 'Unknown', 'email': '', 'date': ''},
                'committer': {'name': 'Unknown', 'email': '', 'date': ''},
                'stats': {'total': 0, 'additions': 0, 'deletions': 0},
                'files': 0,
                'url': web_url,
                'api_url': ''
            }
    
    def get_commit_diff(self, repository_url, commit_sha, access_token=None):
        """Get diff information for a specific commit.
        
        Args:
            repository_url: Full repository URL
            commit_sha: Commit SHA hash
            access_token: Optional access token
            
        Returns:
            dict: Diff information including file changes
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Get commit diff
            diff_data = self._make_request(
                'GET',
                f'projects/{encoded_path}/repository/commits/{commit_sha}/diff',
                repository_url=repository_url,
                access_token=access_token
            )
            
            diff_info = {
                'total_files': len(diff_data),
                'total_additions': 0,
                'total_deletions': 0,
                'files': []
            }
            
            for file_diff in diff_data:
                # Parse diff content to get line counts (basic implementation)
                diff_content = file_diff.get('diff', '')
                additions = diff_content.count('\n+') if diff_content else 0
                deletions = diff_content.count('\n-') if diff_content else 0
                
                diff_info['total_additions'] += additions
                diff_info['total_deletions'] += deletions
                
                # Determine file status
                if file_diff.get('new_file'):
                    status = 'added'
                elif file_diff.get('deleted_file'):
                    status = 'removed'
                elif file_diff.get('renamed_file'):
                    status = 'renamed'
                else:
                    status = 'modified'
                
                diff_info['files'].append({
                    'filename': file_diff.get('new_path', file_diff.get('old_path', 'unknown')),
                    'old_path': file_diff.get('old_path'),
                    'new_path': file_diff.get('new_path'),
                    'status': status,
                    'additions': additions,
                    'deletions': deletions,
                    'changes': additions + deletions,
                    'patch': diff_content
                })
            
            return diff_info
            
        except Exception as e:
            _logger.error(f"Failed to get GitLab commit diff: {str(e)}")
            raise UserError(_('Failed to get commit diff: %s') % str(e))
    
    def search_commits(self, repository_url, query, access_token=None, limit=30):
        """Search commits in GitLab repository.
        
        Args:
            repository_url: Full repository URL
            query: Search query string
            access_token: Optional access token
            limit: Maximum number of results
            
        Returns:
            list: List of matching commits
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # GitLab doesn't have a direct commit search API like GitHub
            # So we'll fetch recent commits and filter by message content
            commits = self.fetch_commits(
                repository_url=repository_url,
                access_token=access_token,
                limit=min(limit * 3, 300)  # Fetch more to filter
            )
            
            # Filter commits by query in message
            matching_commits = []
            query_lower = query.lower()
            
            for commit in commits:
                if (query_lower in commit['message'].lower() or 
                    query_lower in commit['sha'].lower()):
                    
                    matching_commits.append({
                        'sha': commit['sha'],
                        'message': commit['message'],
                        'author': commit['author'],
                        'committer': commit['committer'],
                        'url': commit['url'],
                        'score': 1.0  # Basic scoring - could be improved
                    })
                    
                    if len(matching_commits) >= limit:
                        break
            
            return matching_commits
            
        except Exception as e:
            _logger.error(f"Failed to search GitLab commits: {str(e)}")
            raise UserError(_('Failed to search commits: %s') % str(e))
    
    def get_repository_info(self, repository_url, access_token=None):
        """Get comprehensive repository information.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            dict: Repository information including stats and metadata
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Get project data
            project_data = self._make_request(
                'GET',
                f'projects/{encoded_path}',
                repository_url=repository_url,
                access_token=access_token
            )
            
            # Get project languages
            try:
                languages = self._make_request(
                    'GET',
                    f'projects/{encoded_path}/languages',
                    repository_url=repository_url,
                    access_token=access_token
                )
            except:
                languages = {}
            
            # Get project members (contributors)
            try:
                members = self._make_request(
                    'GET',
                    f'projects/{encoded_path}/members',
                    repository_url=repository_url,
                    access_token=access_token,
                    params={'per_page': 5}
                )
            except:
                members = []
            
            return {
                'basic_info': {
                    'name': project_data['name'],
                    'path_with_namespace': project_data['path_with_namespace'],
                    'description': project_data.get('description', ''),
                    'visibility': project_data.get('visibility', 'private'),
                    'archived': project_data.get('archived', False),
                    'created_at': project_data['created_at'],
                    'last_activity_at': project_data.get('last_activity_at', ''),
                    'default_branch': project_data.get('default_branch', 'main'),
                    'ssh_url_to_repo': project_data.get('ssh_url_to_repo', ''),
                    'http_url_to_repo': project_data.get('http_url_to_repo', ''),
                    'web_url': project_data['web_url']
                },
                'statistics': {
                    'star_count': project_data.get('star_count', 0),
                    'forks_count': project_data.get('forks_count', 0),
                    'open_issues_count': project_data.get('open_issues_count', 0),
                    'repository_size': project_data.get('repository_size', 0),
                    'lfs_size': project_data.get('lfs_size', 0),
                    'job_artifacts_size': project_data.get('job_artifacts_size', 0)
                },
                'languages': languages,
                'top_contributors': [
                    {
                        'name': member.get('name', ''),
                        'username': member.get('username', ''),
                        'access_level': member.get('access_level', 0),
                        'avatar_url': member.get('avatar_url', '')
                    }
                    for member in members[:5]
                ]
            }
            
        except Exception as e:
            _logger.error(f"Failed to get GitLab repository info: {str(e)}")
            raise UserError(_('Failed to get repository information: %s') % str(e))
    
    def _get_project_path(self, repository_url):
        """Extract project path from GitLab repository URL.
        
        Args:
            repository_url: Full repository URL
            
        Returns:
            str: Project path (namespace/project)
            
        Raises:
            ValidationError: If URL format is invalid
        """
        try:
            # Remove .git suffix if present
            url = repository_url.rstrip('/').replace('.git', '')
            
            # Parse URL to get path
            parsed_url = urlparse(url)
            path = parsed_url.path.lstrip('/')
            
            if not path:
                raise ValidationError(_('Unable to extract project path from URL'))
            
            # Split path into parts
            path_parts = path.split('/')
            
            if len(path_parts) < 2:
                raise ValidationError(_('Invalid GitLab repository URL format'))
            
            # Join namespace and project name
            project_path = '/'.join(path_parts[:2])
            
            if not project_path:
                raise ValidationError(_('Unable to extract namespace and project name from URL'))
            
            return project_path
            
        except Exception as e:
            raise ValidationError(_(
                'Invalid GitLab repository URL: %s. '
                'Expected format: https://gitlab.com/namespace/project'
            ) % str(e))
    
    def get_project_statistics(self, repository_url, access_token=None):
        """Get detailed project statistics.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            dict: Detailed statistics
        """
        try:
            project_path = self._get_project_path(repository_url)
            encoded_path = quote(project_path, safe='')
            
            # Get project with statistics
            project_data = self._make_request(
                'GET',
                f'projects/{encoded_path}',
                repository_url=repository_url,
                access_token=access_token,
                params={'statistics': 'true'}
            )
            
            statistics = project_data.get('statistics', {})
            
            return {
                'commit_count': statistics.get('commit_count', 0),
                'storage_size': statistics.get('storage_size', 0),
                'repository_size': statistics.get('repository_size', 0),
                'wiki_size': statistics.get('wiki_size', 0),
                'lfs_objects_size': statistics.get('lfs_objects_size', 0),
                'job_artifacts_size': statistics.get('job_artifacts_size', 0),
                'packages_size': statistics.get('packages_size', 0),
                'snippets_size': statistics.get('snippets_size', 0)
            }
            
        except Exception as e:
            _logger.error(f"Failed to get GitLab project statistics: {str(e)}")
            return {
                'commit_count': 0,
                'storage_size': 0,
                'repository_size': 0,
                'wiki_size': 0,
                'lfs_objects_size': 0,
                'job_artifacts_size': 0,
                'packages_size': 0,
                'snippets_size': 0
            }
    
    def __del__(self):
        """Cleanup session on service destruction."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
