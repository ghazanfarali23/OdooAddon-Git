# -*- coding: utf-8 -*-

import logging
from urllib.parse import urlparse
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GitServiceFactory(models.TransientModel):
    """Factory service for creating appropriate Git platform services.
    
    Provides a unified interface for interacting with different Git platforms
    (GitHub, GitLab, etc.) by automatically detecting the platform and
    returning the appropriate service instance.
    """
    
    _name = 'git.service.factory'
    _description = 'Git Service Factory'
    
    @api.model
    def get_service(self, repository_url):
        """Get the appropriate Git service for a repository URL.
        
        Args:
            repository_url: Full repository URL
            
        Returns:
            object: Service instance (GitHubService or GitLabService)
            
        Raises:
            ValidationError: If repository platform is not supported
        """
        platform = self.detect_platform(repository_url)
        
        if platform == 'github':
            return self.env['github.service']
        elif platform == 'gitlab':
            return self.env['gitlab.service']
        else:
            raise ValidationError(_(
                'Unsupported Git platform: %s. '
                'Currently supported platforms: GitHub, GitLab'
            ) % platform)
    
    @api.model
    def detect_platform(self, repository_url):
        """Detect Git platform from repository URL.
        
        Args:
            repository_url: Full repository URL
            
        Returns:
            str: Platform identifier ('github', 'gitlab', or 'unknown')
        """
        try:
            parsed_url = urlparse(repository_url.lower())
            hostname = parsed_url.netloc
            
            # Remove common prefixes
            hostname = hostname.replace('www.', '')
            
            if 'github.com' in hostname:
                return 'github'
            elif 'gitlab.com' in hostname or 'gitlab' in hostname:
                return 'gitlab'
            else:
                # Check for common GitLab self-hosted patterns
                if any(pattern in hostname for pattern in ['git.', 'source.', 'code.', 'dev.']):
                    # Could be GitLab self-hosted, default to GitLab API
                    return 'gitlab'
                
                return 'unknown'
                
        except Exception as e:
            _logger.error(f"Failed to detect platform for URL {repository_url}: {str(e)}")
            return 'unknown'
    
    @api.model
    def test_connection(self, repository_url, access_token=None):
        """Test connection to repository using appropriate service.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            dict: Connection test result
        """
        try:
            service = self.get_service(repository_url)
            return service.test_connection(repository_url, access_token)
        except Exception as e:
            _logger.error(f"Connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def get_branches(self, repository_url, access_token=None):
        """Get branches using appropriate service.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            list: List of branch dictionaries
        """
        service = self.get_service(repository_url)
        return service.get_branches(repository_url, access_token)
    
    @api.model
    def fetch_commits(self, repository_url, access_token=None, branch='main', 
                     since=None, until=None, author=None, limit=100):
        """Fetch commits using appropriate service.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            branch: Branch name
            since: Start date filter
            until: End date filter
            author: Author filter
            limit: Maximum number of commits
            
        Returns:
            list: List of commit dictionaries
        """
        service = self.get_service(repository_url)
        return service.fetch_commits(
            repository_url=repository_url,
            access_token=access_token,
            branch=branch,
            since=since,
            until=until,
            author=author,
            limit=limit
        )
    
    @api.model
    def get_commit_diff(self, repository_url, commit_sha, access_token=None):
        """Get commit diff using appropriate service.
        
        Args:
            repository_url: Full repository URL
            commit_sha: Commit SHA hash
            access_token: Optional access token
            
        Returns:
            dict: Diff information
        """
        service = self.get_service(repository_url)
        return service.get_commit_diff(repository_url, commit_sha, access_token)
    
    @api.model
    def search_commits(self, repository_url, query, access_token=None, limit=30):
        """Search commits using appropriate service.
        
        Args:
            repository_url: Full repository URL
            query: Search query
            access_token: Optional access token
            limit: Maximum number of results
            
        Returns:
            list: List of matching commits
        """
        service = self.get_service(repository_url)
        return service.search_commits(repository_url, query, access_token, limit)
    
    @api.model
    def get_repository_info(self, repository_url, access_token=None):
        """Get repository information using appropriate service.
        
        Args:
            repository_url: Full repository URL
            access_token: Optional access token
            
        Returns:
            dict: Repository information
        """
        service = self.get_service(repository_url)
        return service.get_repository_info(repository_url, access_token)
    
    @api.model
    def sync_repository_commits(self, git_repository_record):
        """Sync commits for a git.repository record.
        
        This is a high-level method that handles the complete commit
        synchronization workflow for a repository.
        
        Args:
            git_repository_record: git.repository record
            
        Returns:
            dict: Sync result with statistics
        """
        try:
            # Get service for this repository
            service = self.get_service(git_repository_record.repository_url)
            
            # Fetch commits from the repository
            commits_data = service.fetch_commits(
                repository_url=git_repository_record.repository_url,
                access_token=git_repository_record.access_token,
                branch=git_repository_record.default_branch,
                limit=200  # Configurable limit
            )
            
            # Process and store commits
            created_count = 0
            updated_count = 0
            error_count = 0
            
            for commit_data in commits_data:
                try:
                    # Check if commit already exists
                    existing_commit = self.env['git.commit'].search([
                        ('commit_hash', '=', commit_data['sha']),
                        ('repository_id', '=', git_repository_record.id)
                    ])
                    
                    # Prepare commit data for Odoo model
                    commit_values = self._prepare_commit_data(
                        commit_data, git_repository_record
                    )
                    
                    if existing_commit:
                        # Update existing commit
                        existing_commit.write(commit_values)
                        updated_count += 1
                    else:
                        # Create new commit
                        self.env['git.commit'].create(commit_values)
                        created_count += 1
                        
                except Exception as e:
                    _logger.error(f"Failed to process commit {commit_data.get('sha', 'unknown')}: {str(e)}")
                    error_count += 1
            
            # Update repository sync date
            git_repository_record.last_sync_date = self.env.cr.now()
            
            return {
                'success': True,
                'created_commits': created_count,
                'updated_commits': updated_count,
                'error_count': error_count,
                'total_processed': len(commits_data)
            }
            
        except Exception as e:
            _logger.error(f"Repository sync failed for {git_repository_record.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_commits': 0,
                'updated_commits': 0,
                'error_count': 0,
                'total_processed': 0
            }
    
    def _prepare_commit_data(self, commit_data, repository_record):
        """Prepare commit data for Odoo git.commit model.
        
        Args:
            commit_data: Raw commit data from Git service
            repository_record: git.repository record
            
        Returns:
            dict: Prepared data for git.commit model
        """
        # Parse dates
        author_date = self._parse_git_date(commit_data['author']['date'])
        commit_date = self._parse_git_date(commit_data['committer']['date'])
        
        return {
            'repository_id': repository_record.id,
            'commit_hash': commit_data['sha'],
            'author_name': commit_data['author']['name'],
            'author_email': commit_data['author']['email'],
            'committer_name': commit_data['committer']['name'],
            'committer_email': commit_data['committer']['email'],
            'commit_message': commit_data['message'],
            'commit_date': commit_date,
            'author_date': author_date,
            'branch_name': repository_record.default_branch,
            'files_changed': commit_data.get('files', 0),
            'lines_added': commit_data.get('stats', {}).get('additions', 0),
            'lines_deleted': commit_data.get('stats', {}).get('deletions', 0),
            'company_id': repository_record.company_id.id
        }
    
    def _parse_git_date(self, date_string):
        """Parse Git date string to Odoo datetime.
        
        Args:
            date_string: ISO 8601 date string
            
        Returns:
            datetime: Parsed datetime object
        """
        try:
            from datetime import datetime
            # Handle different date formats from Git platforms
            if date_string.endswith('Z'):
                # ISO format with Z timezone
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            elif '+' in date_string or date_string.endswith('UTC'):
                # ISO format with timezone
                return datetime.fromisoformat(date_string.replace('UTC', '+00:00'))
            else:
                # Fallback - assume UTC
                return datetime.fromisoformat(date_string)
        except Exception as e:
            _logger.warning(f"Failed to parse date {date_string}: {str(e)}")
            # Return current time as fallback
            return datetime.now()
    
    @api.model
    def get_supported_platforms(self):
        """Get list of supported Git platforms.
        
        Returns:
            list: List of platform dictionaries
        """
        return [
            {
                'key': 'github',
                'name': 'GitHub',
                'description': 'GitHub.com repositories',
                'base_url': 'https://github.com',
                'api_url': 'https://api.github.com',
                'supports_private': True,
                'supports_enterprise': True,
                'token_name': 'Personal Access Token'
            },
            {
                'key': 'gitlab',
                'name': 'GitLab',
                'description': 'GitLab.com and self-hosted GitLab repositories',
                'base_url': 'https://gitlab.com',
                'api_url': 'https://gitlab.com/api/v4',
                'supports_private': True,
                'supports_enterprise': True,
                'token_name': 'Personal Access Token'
            }
        ]
    
    @api.model
    def validate_repository_url(self, repository_url):
        """Validate repository URL format and accessibility.
        
        Args:
            repository_url: Repository URL to validate
            
        Returns:
            dict: Validation result with details
        """
        try:
            # Basic URL validation
            parsed_url = urlparse(repository_url)
            
            if not parsed_url.scheme in ['http', 'https']:
                return {
                    'valid': False,
                    'error': 'Repository URL must use HTTP or HTTPS protocol'
                }
            
            if not parsed_url.netloc:
                return {
                    'valid': False,
                    'error': 'Invalid repository URL format'
                }
            
            # Platform detection
            platform = self.detect_platform(repository_url)
            
            if platform == 'unknown':
                return {
                    'valid': False,
                    'error': 'Unsupported Git platform. Currently supported: GitHub, GitLab'
                }
            
            # URL pattern validation based on platform
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return {
                    'valid': False,
                    'error': 'Repository URL must include owner/organization and repository name'
                }
            
            return {
                'valid': True,
                'platform': platform,
                'owner': path_parts[0],
                'repository': path_parts[1].replace('.git', ''),
                'url_cleaned': repository_url.rstrip('/').replace('.git', '')
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'URL validation failed: {str(e)}'
            }
    
    @api.model
    def get_platform_documentation(self, platform=None):
        """Get documentation links for Git platform integration.
        
        Args:
            platform: Specific platform or None for all
            
        Returns:
            dict: Documentation links and guides
        """
        docs = {
            'github': {
                'token_creation': 'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token',
                'api_docs': 'https://docs.github.com/en/rest',
                'permissions': 'https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps',
                'rate_limits': 'https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting'
            },
            'gitlab': {
                'token_creation': 'https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html',
                'api_docs': 'https://docs.gitlab.com/ee/api/',
                'permissions': 'https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html#personal-access-token-scopes',
                'rate_limits': 'https://docs.gitlab.com/ee/user/admin_area/settings/user_and_ip_rate_limits.html'
            }
        }
        
        if platform:
            return docs.get(platform, {})
        
        return docs
