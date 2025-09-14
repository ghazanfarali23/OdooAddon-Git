# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class GitTimesheetController(http.Controller):
    """REST API controller for Git Timesheet Mapper functionality.
    
    Provides HTTP endpoints for repository management, commit operations,
    and timesheet mapping functionality. All endpoints return JSON responses
    and require proper authentication and permissions.
    """
    
    # Repository Management Endpoints
    
    @http.route('/git_timesheet_mapper/repository/create', type='json', auth='user', methods=['POST'])
    def repository_create(self, **kwargs):
        """Create a new Git repository configuration.
        
        Expected JSON payload:
        {
            "name": "Repository Display Name",
            "repository_type": "github|gitlab",
            "repository_url": "https://github.com/owner/repo",
            "access_token": "optional_token_for_private_repos",
            "is_private": true|false,
            "project_id": optional_project_id,
            "default_branch": "main"
        }
        
        Returns:
            dict: Created repository data with ID and status
        """
        try:
            # Check permissions
            if not request.env.user.has_group('git_timesheet_mapper.group_git_repository_admin'):
                return {
                    'success': False,
                    'error': _('Insufficient permissions. Repository management requires admin privileges.')
                }
            
            # Validate required fields
            required_fields = ['name', 'repository_type', 'repository_url']
            for field in required_fields:
                if not kwargs.get(field):
                    return {
                        'success': False,
                        'error': _('Missing required field: %s') % field
                    }
            
            # Validate repository URL
            git_factory = request.env['git.service.factory']
            url_validation = git_factory.validate_repository_url(kwargs['repository_url'])
            
            if not url_validation['valid']:
                return {
                    'success': False,
                    'error': url_validation['error']
                }
            
            # Test connection before creating
            connection_test = git_factory.test_connection(
                repository_url=kwargs['repository_url'],
                access_token=kwargs.get('access_token')
            )
            
            if not connection_test['success']:
                return {
                    'success': False,
                    'error': _('Repository connection failed: %s') % connection_test['error']
                }
            
            # Prepare repository data
            repo_data = {
                'name': kwargs['name'],
                'repository_type': kwargs['repository_type'],
                'repository_url': kwargs['repository_url'].rstrip('/'),
                'access_token': kwargs.get('access_token'),
                'is_private': kwargs.get('is_private', False),
                'project_id': kwargs.get('project_id'),
                'default_branch': kwargs.get('default_branch', 'main'),
                'connection_status': 'connected'
            }
            
            # Create repository record
            repository = request.env['git.repository'].create(repo_data)
            
            return {
                'success': True,
                'repository_id': repository.id,
                'repository': {
                    'id': repository.id,
                    'name': repository.name,
                    'repository_type': repository.repository_type,
                    'repository_url': repository.repository_url,
                    'owner': repository.owner,
                    'repo_name': repository.repo_name,
                    'default_branch': repository.default_branch,
                    'connection_status': repository.connection_status,
                    'project_id': repository.project_id.id if repository.project_id else None,
                    'project_name': repository.project_id.name if repository.project_id else None
                },
                'message': _('Repository created successfully')
            }
            
        except ValidationError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            _logger.error(f"Repository creation failed: {str(e)}")
            return {'success': False, 'error': _('Internal server error')}
    
    @http.route('/git_timesheet_mapper/repository/test_connection', type='json', auth='user', methods=['POST'])
    def repository_test_connection(self, **kwargs):
        """Test connection to a Git repository.
        
        Expected JSON payload:
        {
            "repository_url": "https://github.com/owner/repo",
            "access_token": "optional_token"
        }
        
        Returns:
            dict: Connection test results with repository information
        """
        try:
            # Validate required fields
            if not kwargs.get('repository_url'):
                return {
                    'success': False,
                    'error': _('Missing required field: repository_url')
                }
            
            # Test connection using factory service
            git_factory = request.env['git.service.factory']
            connection_result = git_factory.test_connection(
                repository_url=kwargs['repository_url'],
                access_token=kwargs.get('access_token')
            )
            
            if connection_result['success']:
                # Get additional repository information
                repo_info = git_factory.get_repository_info(
                    repository_url=kwargs['repository_url'],
                    access_token=kwargs.get('access_token')
                )
                
                return {
                    'success': True,
                    'connection': connection_result,
                    'repository_info': repo_info,
                    'message': _('Connection successful')
                }
            else:
                return connection_result
                
        except Exception as e:
            _logger.error(f"Connection test failed: {str(e)}")
            return {
                'success': False,
                'error': _('Connection test failed: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/repository/<int:repository_id>/branches', type='json', auth='user', methods=['GET'])
    def repository_get_branches(self, repository_id, **kwargs):
        """Get list of branches for a repository.
        
        Args:
            repository_id: ID of git.repository record
            
        Returns:
            dict: List of branches with metadata
        """
        try:
            # Get repository record
            repository = request.env['git.repository'].browse(repository_id)
            
            if not repository.exists():
                return {
                    'success': False,
                    'error': _('Repository not found')
                }
            
            # Check access rights
            try:
                repository.check_access_rights('read')
                repository.check_access_rule('read')
            except AccessError:
                return {
                    'success': False,
                    'error': _('Access denied to repository')
                }
            
            # Get branches using factory service
            git_factory = request.env['git.service.factory']
            branches = git_factory.get_branches(
                repository_url=repository.repository_url,
                access_token=repository.access_token
            )
            
            return {
                'success': True,
                'repository_id': repository.id,
                'repository_name': repository.name,
                'branches': branches,
                'default_branch': repository.default_branch,
                'total_branches': len(branches)
            }
            
        except Exception as e:
            _logger.error(f"Failed to get branches: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to fetch branches: %s') % str(e)
            }
    
    # Commit Operations Endpoints
    
    @http.route('/git_timesheet_mapper/commits/fetch', type='json', auth='user', methods=['POST'])
    def commits_fetch(self, **kwargs):
        """Fetch commits from a Git repository.
        
        Expected JSON payload:
        {
            "repository_id": 123,
            "branch": "main",
            "since": "2023-01-01T00:00:00Z",
            "until": "2023-12-31T23:59:59Z",
            "author": "optional_author_filter",
            "limit": 100
        }
        
        Returns:
            dict: Fetched commits data and statistics
        """
        try:
            # Validate required fields
            if not kwargs.get('repository_id'):
                return {
                    'success': False,
                    'error': _('Missing required field: repository_id')
                }
            
            # Get repository record
            repository = request.env['git.repository'].browse(kwargs['repository_id'])
            
            if not repository.exists():
                return {
                    'success': False,
                    'error': _('Repository not found')
                }
            
            # Check access rights
            try:
                repository.check_access_rights('read')
                repository.check_access_rule('read')
            except AccessError:
                return {
                    'success': False,
                    'error': _('Access denied to repository')
                }
            
            # Use git factory service to sync commits
            git_factory = request.env['git.service.factory']
            sync_result = git_factory.sync_repository_commits(repository)
            
            if sync_result['success']:
                # Get updated commit statistics
                repository_commits = request.env['git.commit'].search([
                    ('repository_id', '=', repository.id)
                ])
                
                return {
                    'success': True,
                    'repository_id': repository.id,
                    'sync_result': sync_result,
                    'statistics': {
                        'total_commits': len(repository_commits),
                        'mapped_commits': len(repository_commits.filtered('is_mapped')),
                        'unmapped_commits': len(repository_commits.filtered(lambda c: not c.is_mapped)),
                        'last_sync': repository.last_sync_date.isoformat() if repository.last_sync_date else None
                    },
                    'message': _('Commits fetched successfully')
                }
            else:
                return sync_result
                
        except Exception as e:
            _logger.error(f"Commit fetch failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to fetch commits: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/commits/search', type='json', auth='user', methods=['GET'])
    def commits_search(self, **kwargs):
        """Search commits with advanced filtering.
        
        Expected query parameters:
        {
            "repository_id": 123,
            "search_term": "optional_search_in_message_or_hash",
            "branch": "optional_branch_filter",
            "author": "optional_author_filter",
            "date_from": "2023-01-01",
            "date_to": "2023-12-31",
            "commit_type": "feature|bugfix|refactor|docs|test|chore|other",
            "mapped_status": "mapped|unmapped|all",
            "limit": 50,
            "offset": 0
        }
        
        Returns:
            dict: Search results with pagination
        """
        try:
            # Validate required fields
            if not kwargs.get('repository_id'):
                return {
                    'success': False,
                    'error': _('Missing required field: repository_id')
                }
            
            repository_id = kwargs['repository_id']
            
            # Check repository access
            repository = request.env['git.repository'].browse(repository_id)
            if not repository.exists():
                return {
                    'success': False,
                    'error': _('Repository not found')
                }
            
            try:
                repository.check_access_rights('read')
                repository.check_access_rule('read')
            except AccessError:
                return {
                    'success': False,
                    'error': _('Access denied to repository')
                }
            
            # Use git.commit model search method
            commits = request.env['git.commit'].search_commits(
                repository_id=repository_id,
                search_term=kwargs.get('search_term'),
                branch=kwargs.get('branch'),
                author=kwargs.get('author'),
                date_from=kwargs.get('date_from'),
                date_to=kwargs.get('date_to'),
                commit_type=kwargs.get('commit_type'),
                mapped_status=kwargs.get('mapped_status')
            )
            
            # Apply pagination
            limit = min(kwargs.get('limit', 50), 200)  # Max 200 per request
            offset = kwargs.get('offset', 0)
            
            total_count = len(commits)
            paginated_commits = commits[offset:offset + limit]
            
            # Format commit data
            commit_data = []
            for commit in paginated_commits:
                commit_data.append({
                    'id': commit.id,
                    'commit_hash': commit.commit_hash,
                    'short_hash': commit.short_hash,
                    'author_name': commit.author_name,
                    'author_email': commit.author_email,
                    'commit_message': commit.commit_message,
                    'commit_message_short': commit.commit_message_short,
                    'commit_date': commit.commit_date.isoformat() if commit.commit_date else None,
                    'branch_name': commit.branch_name,
                    'commit_type': commit.commit_type,
                    'is_mapped': commit.is_mapped,
                    'mapping_count': commit.mapping_count,
                    'files_changed': commit.files_changed,
                    'lines_added': commit.lines_added,
                    'lines_deleted': commit.lines_deleted,
                    'total_changes': commit.total_changes,
                    'commit_url': commit.commit_url,
                    'time_since_commit': commit.get_time_since_commit()
                })
            
            return {
                'success': True,
                'commits': commit_data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                },
                'repository': {
                    'id': repository.id,
                    'name': repository.name
                }
            }
            
        except Exception as e:
            _logger.error(f"Commit search failed: {str(e)}")
            return {
                'success': False,
                'error': _('Commit search failed: %s') % str(e)
            }
    
    # Mapping Operations Endpoints
    
    @http.route('/git_timesheet_mapper/mapping/create', type='json', auth='user', methods=['POST'])
    def mapping_create(self, **kwargs):
        """Create a single commit to timesheet mapping.
        
        Expected JSON payload:
        {
            "commit_id": 123,
            "timesheet_line_id": 456,
            "description": "Optional mapping description"
        }
        
        Returns:
            dict: Created mapping data
        """
        try:
            # Check permissions
            if not request.env.user.has_group('git_timesheet_mapper.group_git_timesheet_user'):
                return {
                    'success': False,
                    'error': _('Insufficient permissions for timesheet mapping')
                }
            
            # Validate required fields
            required_fields = ['commit_id', 'timesheet_line_id']
            for field in required_fields:
                if not kwargs.get(field):
                    return {
                        'success': False,
                        'error': _('Missing required field: %s') % field
                    }
            
            # Use mapping service
            mapping_service = request.env['mapping.service']
            result = mapping_service.create_mapping(
                commit_id=kwargs['commit_id'],
                timesheet_line_id=kwargs['timesheet_line_id'],
                description=kwargs.get('description')
            )
            
            if result['success']:
                # Get mapping details for response
                mapping = request.env['timesheet.commit.mapping'].browse(result['mapping_id'])
                
                return {
                    'success': True,
                    'mapping_id': mapping.id,
                    'mapping': {
                        'id': mapping.id,
                        'commit_hash': mapping.commit_hash,
                        'commit_message_short': mapping.commit_id.commit_message_short,
                        'timesheet_name': mapping.timesheet_line_id.name,
                        'project_name': mapping.project_id.name if mapping.project_id else None,
                        'mapping_date': mapping.mapping_date.isoformat(),
                        'mapped_by': mapping.mapped_by.name,
                        'description': mapping.description
                    },
                    'message': result['message']
                }
            else:
                return result
                
        except Exception as e:
            _logger.error(f"Mapping creation failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to create mapping: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/mapping/bulk_create', type='json', auth='user', methods=['POST'])
    def mapping_bulk_create(self, **kwargs):
        """Create multiple commit mappings to a single timesheet.
        
        Expected JSON payload:
        {
            "commit_ids": [123, 456, 789],
            "timesheet_line_id": 456,
            "description": "Optional bulk mapping description"
        }
        
        Returns:
            dict: Bulk creation results with statistics
        """
        try:
            # Check permissions
            if not request.env.user.has_group('git_timesheet_mapper.group_git_timesheet_user'):
                return {
                    'success': False,
                    'error': _('Insufficient permissions for timesheet mapping')
                }
            
            # Validate required fields
            required_fields = ['commit_ids', 'timesheet_line_id']
            for field in required_fields:
                if not kwargs.get(field):
                    return {
                        'success': False,
                        'error': _('Missing required field: %s') % field
                    }
            
            if not isinstance(kwargs['commit_ids'], list) or not kwargs['commit_ids']:
                return {
                    'success': False,
                    'error': _('commit_ids must be a non-empty list')
                }
            
            # Use mapping service
            mapping_service = request.env['mapping.service']
            result = mapping_service.create_bulk_mappings(
                commit_ids=kwargs['commit_ids'],
                timesheet_line_id=kwargs['timesheet_line_id'],
                description=kwargs.get('description')
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Bulk mapping creation failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to create bulk mappings: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/mapping/<int:mapping_id>', type='json', auth='user', methods=['DELETE'])
    def mapping_delete(self, mapping_id, **kwargs):
        """Delete a commit to timesheet mapping.
        
        Args:
            mapping_id: ID of timesheet.commit.mapping record
            
        Returns:
            dict: Deletion result
        """
        try:
            # Use mapping service
            mapping_service = request.env['mapping.service']
            result = mapping_service.remove_mapping(mapping_id)
            
            return result
            
        except Exception as e:
            _logger.error(f"Mapping deletion failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to delete mapping: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/mapping/suggestions', type='json', auth='user', methods=['POST'])
    def mapping_suggestions(self, **kwargs):
        """Get intelligent mapping suggestions.
        
        Expected JSON payload:
        {
            "commit_ids": [123, 456],  # Optional: specific commits
            "timesheet_line_ids": [789, 101],  # Optional: specific timesheets
            "limit": 10
        }
        
        Returns:
            dict: Mapping suggestions with confidence scores
        """
        try:
            # Check permissions
            if not request.env.user.has_group('git_timesheet_mapper.group_git_timesheet_user'):
                return {
                    'success': False,
                    'error': _('Insufficient permissions for mapping suggestions')
                }
            
            # Use mapping service
            mapping_service = request.env['mapping.service']
            result = mapping_service.suggest_mappings(
                commit_ids=kwargs.get('commit_ids'),
                timesheet_line_ids=kwargs.get('timesheet_line_ids'),
                limit=kwargs.get('limit', 10)
            )
            
            return result
            
        except Exception as e:
            _logger.error(f"Mapping suggestions failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to generate suggestions: %s') % str(e)
            }
    
    # Statistics and Dashboard Endpoints
    
    @http.route('/git_timesheet_mapper/statistics/overview', type='json', auth='user', methods=['GET'])
    def statistics_overview(self, **kwargs):
        """Get overview statistics for Git timesheet mapping.
        
        Expected query parameters:
        {
            "project_id": 123,  # Optional: filter by project
            "user_id": 456,     # Optional: filter by user
            "date_from": "2023-01-01",  # Optional: start date
            "date_to": "2023-12-31"     # Optional: end date
        }
        
        Returns:
            dict: Comprehensive statistics and metrics
        """
        try:
            # Build filter data
            filter_data = {}
            if kwargs.get('project_id'):
                filter_data['project_id'] = kwargs['project_id']
            if kwargs.get('user_id'):
                filter_data['user_id'] = kwargs['user_id']
            if kwargs.get('date_from'):
                filter_data['date_from'] = kwargs['date_from']
            if kwargs.get('date_to'):
                filter_data['date_to'] = kwargs['date_to']
            
            # Get mapping statistics
            mapping_service = request.env['mapping.service']
            mapping_stats = mapping_service.get_mapping_statistics(filter_data)
            
            # Get commit statistics
            commit_stats = request.env['git.commit'].get_commit_statistics(
                repository_id=None,  # All repositories
                date_from=filter_data.get('date_from'),
                date_to=filter_data.get('date_to')
            )
            
            # Get repository counts
            repositories = request.env['git.repository'].search([])
            active_repositories = repositories.filtered(lambda r: r.connection_status == 'connected')
            
            # Recent activity
            recent_mappings = request.env['timesheet.commit.mapping'].search([
                ('mapping_date', '>=', (datetime.now() - timedelta(days=7)).isoformat())
            ], limit=10, order='mapping_date desc')
            
            recent_activity = []
            for mapping in recent_mappings:
                recent_activity.append({
                    'id': mapping.id,
                    'commit_hash': mapping.commit_hash,
                    'timesheet_name': mapping.timesheet_line_id.name,
                    'project_name': mapping.project_id.name if mapping.project_id else None,
                    'mapped_by': mapping.mapped_by.name,
                    'mapping_date': mapping.mapping_date.isoformat(),
                    'mapping_method': mapping.mapping_method
                })
            
            return {
                'success': True,
                'statistics': {
                    'overview': {
                        'total_repositories': len(repositories),
                        'active_repositories': len(active_repositories),
                        'total_commits': commit_stats['total_commits'],
                        'mapped_commits': commit_stats['mapped_commits'],
                        'unmapped_commits': commit_stats['unmapped_commits'],
                        'mapping_percentage': (commit_stats['mapped_commits'] / max(commit_stats['total_commits'], 1)) * 100
                    },
                    'mappings': mapping_stats['statistics'] if mapping_stats['success'] else {},
                    'commits': commit_stats,
                    'recent_activity': recent_activity
                },
                'filters_applied': filter_data
            }
            
        except Exception as e:
            _logger.error(f"Statistics overview failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to get statistics: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/statistics/repositories', type='json', auth='user', methods=['GET'])
    def statistics_repositories(self, **kwargs):
        """Get repository-specific statistics.
        
        Returns:
            dict: Per-repository statistics and health metrics
        """
        try:
            repositories = request.env['git.repository'].search([])
            
            repository_stats = []
            for repo in repositories:
                commits = request.env['git.commit'].search([('repository_id', '=', repo.id)])
                
                repository_stats.append({
                    'id': repo.id,
                    'name': repo.name,
                    'repository_type': repo.repository_type,
                    'connection_status': repo.connection_status,
                    'project_name': repo.project_id.name if repo.project_id else None,
                    'last_sync_date': repo.last_sync_date.isoformat() if repo.last_sync_date else None,
                    'statistics': {
                        'total_commits': len(commits),
                        'mapped_commits': len(commits.filtered('is_mapped')),
                        'unmapped_commits': len(commits.filtered(lambda c: not c.is_mapped)),
                        'unique_authors': len(set(commits.mapped('author_name'))),
                        'total_lines_changed': sum(commits.mapped('total_changes')),
                        'avg_files_per_commit': sum(commits.mapped('files_changed')) / max(len(commits), 1)
                    }
                })
            
            return {
                'success': True,
                'repositories': repository_stats,
                'summary': {
                    'total_repositories': len(repositories),
                    'connected_repositories': len([r for r in repository_stats if r['connection_status'] == 'connected']),
                    'repositories_with_commits': len([r for r in repository_stats if r['statistics']['total_commits'] > 0])
                }
            }
            
        except Exception as e:
            _logger.error(f"Repository statistics failed: {str(e)}")
            return {
                'success': False,
                'error': _('Failed to get repository statistics: %s') % str(e)
            }
    
    @http.route('/git_timesheet_mapper/health', type='http', auth='public', methods=['GET'])
    def health_check(self, **kwargs):
        """Health check endpoint for monitoring.
        
        Returns:
            str: Health status response
        """
        try:
            # Basic health checks
            checks = {
                'database': True,  # If we get here, DB is accessible
                'git_models': True,
                'services': True
            }
            
            # Test model access
            try:
                request.env['git.repository'].search([], limit=1)
            except Exception:
                checks['git_models'] = False
            
            # Test service access
            try:
                request.env['git.service.factory'].get_supported_platforms()
            except Exception:
                checks['services'] = False
            
            status = 'healthy' if all(checks.values()) else 'degraded'
            
            response_data = {
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'checks': checks,
                'version': '1.0.0'
            }
            
            return json.dumps(response_data)
            
        except Exception as e:
            _logger.error(f"Health check failed: {str(e)}")
            return json.dumps({
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
    
    # Utility Methods
    
    def _format_error_response(self, error_message, error_code=None):
        """Format standardized error response.
        
        Args:
            error_message: Human-readable error message
            error_code: Optional error code for client handling
            
        Returns:
            dict: Formatted error response
        """
        return {
            'success': False,
            'error': error_message,
            'error_code': error_code,
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_rate_limits(self, user_id, endpoint):
        """Check if user has exceeded rate limits for endpoint.
        
        Args:
            user_id: User ID
            endpoint: Endpoint name
            
        Returns:
            bool: True if within limits, False if exceeded
        """
        # Implementation would depend on rate limiting strategy
        # For now, return True (no limits)
        return True
