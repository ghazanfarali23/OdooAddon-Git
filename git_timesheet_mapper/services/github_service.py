# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime, timezone
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GitHubService(models.TransientModel):
    """GitHub API service for repository operations.
    
    Provides methods for connecting to GitHub repositories,
    fetching commits, branches, and other repository data.
    Uses GitHub REST API v4 with authentication support.
    """
    
    _name = 'github.service'
    _description = 'GitHub API Service'
    
    def __init__(self, pool, cr):
        """Initialize GitHub service."""
        super().__init__(pool, cr)
        self.base_url = 'https://api.github.com'
        self.session = None
    
    def _get_session(self, access_token=None):
        """Get configured requests session with authentication.
        
        Args:
            access_token: GitHub personal access token
            
        Returns:
            requests.Session: Configured session
        """
        if not self.session:
            self.session = requests.Session()
            self.session.headers.update({
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Odoo-Git-Timesheet-Mapper/1.0'
            })
        
        if access_token:
            self.session.headers['Authorization'] = f'token {access_token}'
        elif 'Authorization' in self.session.headers:
            # Remove old token if no new token provided
            del self.session.headers['Authorization']
        
        return self.session
    
    def _make_request(self, method, url, access_token=None, **kwargs):
        """Make authenticated request to GitHub API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or path relative to base_url
            access_token: Optional access token
            **kwargs: Additional arguments for requests
            
        Returns:
            dict: JSON response data
            
        Raises:
            UserError: For API errors or network issues
        """
        if not url.startswith('http'):
            url = f"{self.base_url}/{url.lstrip('/')}"
        
        session = self._get_session(access_token)
        
        try:
            response = session.request(method, url, timeout=30, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                raise UserError(_(
                    'GitHub API rate limit exceeded. Limit will reset at: %s'
                ) % reset_time)
            
            # Handle authentication errors
            if response.status_code == 401:
                raise UserError(_('GitHub authentication failed. Please check your access token.'))
            
            # Handle not found
            if response.status_code == 404:
                raise UserError(_('GitHub repository not found or not accessible.'))
            
            # Handle other client errors
            if 400 <= response.status_code < 500:
                error_msg = response.json().get('message', 'Unknown client error')
                raise UserError(_('GitHub API error: %s') % error_msg)
            
            # Handle server errors
            if response.status_code >= 500:
                raise UserError(_('GitHub server error. Please try again later.'))
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise UserError(_('GitHub API request timed out. Please check your connection.'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Unable to connect to GitHub API. Please check your internet connection.'))
        except requests.exceptions.RequestException as e:
            raise UserError(_('GitHub API request failed: %s') % str(e))
    
    def test_connection(self, repository_url, access_token=None):
        """Test connection to GitHub repository.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token for private repos
            
        Returns:
            dict: Connection test result with success status and details
        """
        try:
            owner, repo = self._parse_repository_url(repository_url)
            
            # Get repository information
            repo_data = self._make_request(
                'GET', 
                f'repos/{owner}/{repo}',
                access_token=access_token
            )
            
            return {
                'success': True,
                'repository': {
                    'name': repo_data['name'],
                    'full_name': repo_data['full_name'],
                    'description': repo_data.get('description', ''),
                    'private': repo_data['private'],
                    'default_branch': repo_data['default_branch'],
                    'language': repo_data.get('language', ''),
                    'stars': repo_data['stargazers_count'],
                    'forks': repo_data['forks_count'],
                    'created_at': repo_data['created_at'],
                    'updated_at': repo_data['updated_at']
                }
            }
            
        except Exception as e:
            _logger.error(f"GitHub connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_branches(self, repository_url, access_token=None):
        """Get list of branches from GitHub repository.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            list: List of branch dictionaries with name and commit info
        """
        try:
            owner, repo = self._parse_repository_url(repository_url)
            
            # Get branches with pagination support
            branches = []
            page = 1
            per_page = 100
            
            while True:
                branch_data = self._make_request(
                    'GET',
                    f'repos/{owner}/{repo}/branches',
                    access_token=access_token,
                    params={'page': page, 'per_page': per_page}
                )
                
                if not branch_data:
                    break
                
                for branch in branch_data:
                    branches.append({
                        'name': branch['name'],
                        'commit_sha': branch['commit']['sha'],
                        'protected': branch.get('protected', False)
                    })
                
                # Check if we have more pages
                if len(branch_data) < per_page:
                    break
                
                page += 1
            
            return branches
            
        except Exception as e:
            _logger.error(f"Failed to fetch GitHub branches: {str(e)}")
            raise UserError(_('Failed to fetch branches: %s') % str(e))
    
    def fetch_commits(self, repository_url, access_token=None, branch='main', 
                     since=None, until=None, author=None, limit=100):
        """Fetch commits from GitHub repository.
        
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
            owner, repo = self._parse_repository_url(repository_url)
            
            # Build parameters for commit fetching
            params = {
                'sha': branch,
                'per_page': min(limit, 100)  # GitHub max per page is 100
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
                    f'repos/{owner}/{repo}/commits',
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
                        owner, repo, commit['sha'], access_token
                    )
                    
                    commits.append(detailed_commit)
                
                # Check if we have more pages
                if len(commit_data) < params['per_page']:
                    break
                
                page += 1
            
            return commits[:limit]
            
        except Exception as e:
            _logger.error(f"Failed to fetch GitHub commits: {str(e)}")
            raise UserError(_('Failed to fetch commits: %s') % str(e))
    
    def _get_commit_details(self, owner, repo, commit_sha, access_token=None):
        """Get detailed information for a specific commit.
        
        Args:
            owner: Repository owner
            repo: Repository name
            commit_sha: Commit SHA hash
            access_token: Optional access token
            
        Returns:
            dict: Detailed commit information
        """
        try:
            commit_data = self._make_request(
                'GET',
                f'repos/{owner}/{repo}/commits/{commit_sha}',
                access_token=access_token
            )
            
            # Parse commit data
            commit_info = commit_data['commit']
            author_info = commit_info['author']
            committer_info = commit_info['committer']
            
            # Get file statistics
            stats = commit_data.get('stats', {})
            files = commit_data.get('files', [])
            
            return {
                'sha': commit_data['sha'],
                'message': commit_info['message'],
                'author': {
                    'name': author_info['name'],
                    'email': author_info['email'],
                    'date': author_info['date']
                },
                'committer': {
                    'name': committer_info['name'],
                    'email': committer_info['email'],
                    'date': committer_info['date']
                },
                'stats': {
                    'total': stats.get('total', 0),
                    'additions': stats.get('additions', 0),
                    'deletions': stats.get('deletions', 0)
                },
                'files': len(files),
                'url': commit_data['html_url'],
                'api_url': commit_data['url']
            }
            
        except Exception as e:
            _logger.warning(f"Failed to get detailed commit info for {commit_sha}: {str(e)}")
            # Return basic info if detailed fetch fails
            return {
                'sha': commit_sha,
                'message': 'Unable to fetch detailed information',
                'author': {'name': 'Unknown', 'email': '', 'date': ''},
                'committer': {'name': 'Unknown', 'email': '', 'date': ''},
                'stats': {'total': 0, 'additions': 0, 'deletions': 0},
                'files': 0,
                'url': f'https://github.com/{owner}/{repo}/commit/{commit_sha}',
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
            owner, repo = self._parse_repository_url(repository_url)
            
            commit_data = self._make_request(
                'GET',
                f'repos/{owner}/{repo}/commits/{commit_sha}',
                access_token=access_token
            )
            
            files = commit_data.get('files', [])
            
            diff_info = {
                'total_files': len(files),
                'total_additions': commit_data.get('stats', {}).get('additions', 0),
                'total_deletions': commit_data.get('stats', {}).get('deletions', 0),
                'files': []
            }
            
            for file_info in files:
                diff_info['files'].append({
                    'filename': file_info['filename'],
                    'status': file_info['status'],  # added, removed, modified, renamed
                    'additions': file_info.get('additions', 0),
                    'deletions': file_info.get('deletions', 0),
                    'changes': file_info.get('changes', 0),
                    'patch': file_info.get('patch', '')  # Actual diff content
                })
            
            return diff_info
            
        except Exception as e:
            _logger.error(f"Failed to get GitHub commit diff: {str(e)}")
            raise UserError(_('Failed to get commit diff: %s') % str(e))
    
    def search_commits(self, repository_url, query, access_token=None, limit=30):
        """Search commits in GitHub repository.
        
        Args:
            repository_url: Full repository URL
            query: Search query string
            access_token: Optional access token
            limit: Maximum number of results
            
        Returns:
            list: List of matching commits
        """
        try:
            owner, repo = self._parse_repository_url(repository_url)
            
            # Use GitHub search API for commits
            search_query = f'{query} repo:{owner}/{repo}'
            
            search_results = self._make_request(
                'GET',
                'search/commits',
                access_token=access_token,
                params={
                    'q': search_query,
                    'per_page': min(limit, 100),
                    'sort': 'committer-date',
                    'order': 'desc'
                }
            )
            
            commits = []
            for item in search_results.get('items', []):
                commits.append({
                    'sha': item['sha'],
                    'message': item['commit']['message'],
                    'author': {
                        'name': item['commit']['author']['name'],
                        'email': item['commit']['author']['email'],
                        'date': item['commit']['author']['date']
                    },
                    'committer': {
                        'name': item['commit']['committer']['name'], 
                        'email': item['commit']['committer']['email'],
                        'date': item['commit']['committer']['date']
                    },
                    'url': item['html_url'],
                    'score': item.get('score', 0)  # Search relevance score
                })
            
            return commits[:limit]
            
        except Exception as e:
            _logger.error(f"Failed to search GitHub commits: {str(e)}")
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
            owner, repo = self._parse_repository_url(repository_url)
            
            # Get repository data
            repo_data = self._make_request(
                'GET',
                f'repos/{owner}/{repo}',
                access_token=access_token
            )
            
            # Get additional statistics
            contributors = self._make_request(
                'GET',
                f'repos/{owner}/{repo}/contributors',
                access_token=access_token,
                params={'per_page': 5}  # Top 5 contributors
            )
            
            languages = self._make_request(
                'GET',
                f'repos/{owner}/{repo}/languages',
                access_token=access_token
            )
            
            return {
                'basic_info': {
                    'name': repo_data['name'],
                    'full_name': repo_data['full_name'],
                    'description': repo_data.get('description', ''),
                    'private': repo_data['private'],
                    'fork': repo_data['fork'],
                    'created_at': repo_data['created_at'],
                    'updated_at': repo_data['updated_at'],
                    'pushed_at': repo_data['pushed_at'],
                    'default_branch': repo_data['default_branch'],
                    'clone_url': repo_data['clone_url'],
                    'html_url': repo_data['html_url']
                },
                'statistics': {
                    'size': repo_data['size'],  # in KB
                    'stargazers_count': repo_data['stargazers_count'],
                    'watchers_count': repo_data['watchers_count'],
                    'forks_count': repo_data['forks_count'],
                    'open_issues_count': repo_data['open_issues_count'],
                    'subscribers_count': repo_data.get('subscribers_count', 0)
                },
                'languages': languages,
                'top_contributors': [
                    {
                        'login': contributor['login'],
                        'contributions': contributor['contributions'],
                        'avatar_url': contributor['avatar_url']
                    }
                    for contributor in contributors[:5]
                ]
            }
            
        except Exception as e:
            _logger.error(f"Failed to get GitHub repository info: {str(e)}")
            raise UserError(_('Failed to get repository information: %s') % str(e))
    
    def _parse_repository_url(self, repository_url):
        """Parse GitHub repository URL to extract owner and repo name.
        
        Args:
            repository_url: Full repository URL
            
        Returns:
            tuple: (owner, repo_name)
            
        Raises:
            ValidationError: If URL format is invalid
        """
        try:
            # Remove .git suffix if present
            url = repository_url.rstrip('/').replace('.git', '')
            
            # Extract path from URL
            if 'github.com' not in url:
                raise ValidationError(_('Not a valid GitHub URL'))
            
            # Parse URL path
            path_parts = url.split('github.com/')[-1].split('/')
            
            if len(path_parts) < 2:
                raise ValidationError(_('Invalid GitHub repository URL format'))
            
            owner = path_parts[0]
            repo = path_parts[1]
            
            if not owner or not repo:
                raise ValidationError(_('Unable to extract owner and repository name from URL'))
            
            return owner, repo
            
        except Exception as e:
            raise ValidationError(_(
                'Invalid GitHub repository URL: %s. '
                'Expected format: https://github.com/owner/repository'
            ) % str(e))
    
    def get_rate_limit_info(self, access_token=None):
        """Get current rate limit information.
        
        Args:
            access_token: Optional access token
            
        Returns:
            dict: Rate limit information
        """
        try:
            rate_limit_data = self._make_request(
                'GET',
                'rate_limit',
                access_token=access_token
            )
            
            core_limit = rate_limit_data['resources']['core']
            search_limit = rate_limit_data['resources']['search']
            
            return {
                'core': {
                    'limit': core_limit['limit'],
                    'remaining': core_limit['remaining'],
                    'reset': datetime.fromtimestamp(core_limit['reset'], tz=timezone.utc),
                    'used': core_limit['used']
                },
                'search': {
                    'limit': search_limit['limit'],
                    'remaining': search_limit['remaining'],
                    'reset': datetime.fromtimestamp(search_limit['reset'], tz=timezone.utc),
                    'used': search_limit['used']
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to get GitHub rate limit info: {str(e)}")
            return {
                'core': {'limit': 0, 'remaining': 0, 'reset': None, 'used': 0},
                'search': {'limit': 0, 'remaining': 0, 'reset': None, 'used': 0}
            }
    
    def __del__(self):
        """Cleanup session on service destruction."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
