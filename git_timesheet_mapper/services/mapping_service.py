# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MappingService(models.TransientModel):
    """Service for managing commit to timesheet mappings.
    
    Provides business logic for creating, managing, and optimizing
    the mapping between Git commits and timesheet entries.
    Includes bulk operations, smart suggestions, and validation.
    """
    
    _name = 'mapping.service'
    _description = 'Commit Mapping Service'
    
    @api.model
    def create_mapping(self, commit_id, timesheet_line_id, description=None):
        """Create a single commit to timesheet mapping.
        
        Args:
            commit_id: ID of git.commit record
            timesheet_line_id: ID of account.analytic.line record
            description: Optional mapping description
            
        Returns:
            dict: Result with mapping record and success status
        """
        try:
            # Validate inputs
            commit = self.env['git.commit'].browse(commit_id)
            timesheet = self.env['account.analytic.line'].browse(timesheet_line_id)
            
            if not commit.exists():
                raise ValidationError(_('Commit not found'))
            
            if not timesheet.exists():
                raise ValidationError(_('Timesheet entry not found'))
            
            # Check if commit is already mapped
            existing_mapping = self.env['timesheet.commit.mapping'].search([
                ('commit_id', '=', commit_id)
            ])
            
            if existing_mapping:
                raise ValidationError(_(
                    'Commit %s is already mapped to timesheet: %s'
                ) % (commit.short_hash, existing_mapping.timesheet_line_id.name))
            
            # Validate business rules
            self._validate_mapping_rules(commit, timesheet)
            
            # Create the mapping
            mapping_data = {
                'commit_id': commit_id,
                'timesheet_line_id': timesheet_line_id,
                'description': description or f'Manual mapping: {commit.short_hash}',
                'mapping_method': 'manual',
                'mapped_by': self.env.user.id
            }
            
            mapping = self.env['timesheet.commit.mapping'].create(mapping_data)
            
            return {
                'success': True,
                'mapping_id': mapping.id,
                'message': _('Commit successfully mapped to timesheet')
            }
            
        except Exception as e:
            _logger.error(f"Failed to create mapping: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def create_bulk_mappings(self, commit_ids, timesheet_line_id, description=None):
        """Create multiple commit mappings to a single timesheet.
        
        Args:
            commit_ids: List of git.commit IDs
            timesheet_line_id: ID of account.analytic.line record
            description: Optional description for all mappings
            
        Returns:
            dict: Result with statistics and any errors
        """
        try:
            timesheet = self.env['account.analytic.line'].browse(timesheet_line_id)
            if not timesheet.exists():
                raise ValidationError(_('Timesheet entry not found'))
            
            created_mappings = []
            failed_mappings = []
            skipped_mappings = []
            
            for commit_id in commit_ids:
                try:
                    commit = self.env['git.commit'].browse(commit_id)
                    if not commit.exists():
                        failed_mappings.append({
                            'commit_id': commit_id,
                            'error': 'Commit not found'
                        })
                        continue
                    
                    # Check if already mapped
                    existing_mapping = self.env['timesheet.commit.mapping'].search([
                        ('commit_id', '=', commit_id)
                    ])
                    
                    if existing_mapping:
                        skipped_mappings.append({
                            'commit_id': commit_id,
                            'commit_hash': commit.short_hash,
                            'reason': f'Already mapped to {existing_mapping.timesheet_line_id.name}'
                        })
                        continue
                    
                    # Validate business rules
                    validation_result = self._validate_mapping_rules(commit, timesheet, raise_error=False)
                    if not validation_result['valid']:
                        failed_mappings.append({
                            'commit_id': commit_id,
                            'commit_hash': commit.short_hash,
                            'error': validation_result['error']
                        })
                        continue
                    
                    # Create mapping
                    mapping_data = {
                        'commit_id': commit_id,
                        'timesheet_line_id': timesheet_line_id,
                        'description': description or f'Bulk mapping: {commit.short_hash}',
                        'mapping_method': 'bulk',
                        'mapped_by': self.env.user.id
                    }
                    
                    mapping = self.env['timesheet.commit.mapping'].create(mapping_data)
                    created_mappings.append({
                        'mapping_id': mapping.id,
                        'commit_id': commit_id,
                        'commit_hash': commit.short_hash
                    })
                    
                except Exception as e:
                    failed_mappings.append({
                        'commit_id': commit_id,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'created_count': len(created_mappings),
                'failed_count': len(failed_mappings),
                'skipped_count': len(skipped_mappings),
                'created_mappings': created_mappings,
                'failed_mappings': failed_mappings,
                'skipped_mappings': skipped_mappings,
                'message': _(
                    'Bulk mapping completed: %d created, %d failed, %d skipped'
                ) % (len(created_mappings), len(failed_mappings), len(skipped_mappings))
            }
            
        except Exception as e:
            _logger.error(f"Bulk mapping failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_count': 0,
                'failed_count': 0,
                'skipped_count': 0
            }
    
    @api.model
    def suggest_mappings(self, commit_ids=None, timesheet_line_ids=None, limit=10):
        """Generate intelligent mapping suggestions.
        
        Args:
            commit_ids: Optional list of specific commit IDs to suggest for
            timesheet_line_ids: Optional list of specific timesheet IDs to suggest for
            limit: Maximum suggestions per commit/timesheet
            
        Returns:
            dict: Mapping suggestions with confidence scores
        """
        try:
            suggestions = {
                'commit_suggestions': {},  # commit_id -> list of timesheet suggestions
                'timesheet_suggestions': {},  # timesheet_id -> list of commit suggestions
                'auto_mappings': []  # High-confidence automatic suggestions
            }
            
            # Get unmapped commits
            commit_domain = [('is_mapped', '=', False)]
            if commit_ids:
                commit_domain.append(('id', 'in', commit_ids))
            
            commits = self.env['git.commit'].search(commit_domain)
            
            # Get timesheets from recent period
            timesheet_domain = [
                ('project_id', '!=', False),
                ('date', '>=', (datetime.now() - timedelta(days=30)).date())
            ]
            if timesheet_line_ids:
                timesheet_domain.append(('id', 'in', timesheet_line_ids))
            
            timesheets = self.env['account.analytic.line'].search(timesheet_domain)
            
            # Generate suggestions for each commit
            for commit in commits:
                commit_suggestions = self._generate_commit_suggestions(commit, timesheets, limit)
                if commit_suggestions:
                    suggestions['commit_suggestions'][commit.id] = commit_suggestions
                    
                    # Check for auto-mapping candidates (high confidence)
                    auto_candidates = [s for s in commit_suggestions if s['confidence_score'] >= 0.8]
                    if auto_candidates:
                        suggestions['auto_mappings'].extend([
                            {
                                'commit_id': commit.id,
                                'timesheet_id': candidate['timesheet_id'],
                                'confidence_score': candidate['confidence_score'],
                                'reasons': candidate['reasons']
                            }
                            for candidate in auto_candidates[:1]  # Only top candidate
                        ])
            
            # Generate suggestions for each timesheet
            for timesheet in timesheets:
                timesheet_suggestions = self._generate_timesheet_suggestions(timesheet, commits, limit)
                if timesheet_suggestions:
                    suggestions['timesheet_suggestions'][timesheet.id] = timesheet_suggestions
            
            return {
                'success': True,
                'suggestions': suggestions,
                'stats': {
                    'commits_analyzed': len(commits),
                    'timesheets_analyzed': len(timesheets),
                    'commit_suggestions_count': len(suggestions['commit_suggestions']),
                    'timesheet_suggestions_count': len(suggestions['timesheet_suggestions']),
                    'auto_mapping_candidates': len(suggestions['auto_mappings'])
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to generate suggestions: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'suggestions': {}
            }
    
    def _generate_commit_suggestions(self, commit, timesheets, limit):
        """Generate timesheet suggestions for a specific commit.
        
        Args:
            commit: git.commit record
            timesheets: account.analytic.line recordset
            limit: Maximum number of suggestions
            
        Returns:
            list: List of suggestion dictionaries
        """
        suggestions = []
        
        for timesheet in timesheets:
            score = self._calculate_mapping_score(commit, timesheet)
            
            if score > 0.3:  # Minimum confidence threshold
                suggestions.append({
                    'timesheet_id': timesheet.id,
                    'timesheet_name': timesheet.name,
                    'project_name': timesheet.project_id.name,
                    'task_name': timesheet.task_id.name if timesheet.task_id else '',
                    'user_name': timesheet.user_id.name,
                    'date': timesheet.date.isoformat(),
                    'hours': timesheet.unit_amount,
                    'confidence_score': score,
                    'reasons': self._get_mapping_reasons(commit, timesheet, score)
                })
        
        # Sort by confidence score and return top suggestions
        suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)
        return suggestions[:limit]
    
    def _generate_timesheet_suggestions(self, timesheet, commits, limit):
        """Generate commit suggestions for a specific timesheet.
        
        Args:
            timesheet: account.analytic.line record
            commits: git.commit recordset
            limit: Maximum number of suggestions
            
        Returns:
            list: List of suggestion dictionaries
        """
        suggestions = []
        
        for commit in commits:
            score = self._calculate_mapping_score(commit, timesheet)
            
            if score > 0.3:  # Minimum confidence threshold
                suggestions.append({
                    'commit_id': commit.id,
                    'commit_hash': commit.short_hash,
                    'commit_message': commit.commit_message_short,
                    'author_name': commit.author_name,
                    'commit_date': commit.commit_date.isoformat() if commit.commit_date else '',
                    'repository_name': commit.repository_id.name,
                    'confidence_score': score,
                    'reasons': self._get_mapping_reasons(commit, timesheet, score)
                })
        
        # Sort by confidence score and return top suggestions
        suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)
        return suggestions[:limit]
    
    def _calculate_mapping_score(self, commit, timesheet):
        """Calculate confidence score for commit-timesheet mapping.
        
        Args:
            commit: git.commit record
            timesheet: account.analytic.line record
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Project match (highest weight) - 40%
        if (commit.repository_id.project_id and 
            commit.repository_id.project_id == timesheet.project_id):
            score += 0.4
        
        # Author email match - 30%
        if (commit.author_email and timesheet.user_id.email and 
            commit.author_email.lower() == timesheet.user_id.email.lower()):
            score += 0.3
        
        # Date proximity - 20%
        if commit.commit_date and timesheet.date:
            commit_date = commit.commit_date.date()
            timesheet_date = timesheet.date
            date_diff = abs((commit_date - timesheet_date).days)
            
            if date_diff == 0:
                score += 0.2
            elif date_diff <= 1:
                score += 0.15
            elif date_diff <= 3:
                score += 0.1
            elif date_diff <= 7:
                score += 0.05
        
        # Keyword matching - 10%
        if commit.commit_message and timesheet.name:
            commit_words = set(commit.commit_message.lower().split())
            timesheet_words = set(timesheet.name.lower().split())
            common_words = commit_words.intersection(timesheet_words)
            
            if common_words:
                keyword_score = min(0.1, len(common_words) * 0.02)
                score += keyword_score
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_mapping_reasons(self, commit, timesheet, score):
        """Get human-readable reasons for mapping suggestion.
        
        Args:
            commit: git.commit record
            timesheet: account.analytic.line record
            score: Calculated confidence score
            
        Returns:
            list: List of reason strings
        """
        reasons = []
        
        # Project match
        if (commit.repository_id.project_id and 
            commit.repository_id.project_id == timesheet.project_id):
            reasons.append(_('Same project: %s') % timesheet.project_id.name)
        
        # Author match
        if (commit.author_email and timesheet.user_id.email and 
            commit.author_email.lower() == timesheet.user_id.email.lower()):
            reasons.append(_('Author matches timesheet user'))
        
        # Date proximity
        if commit.commit_date and timesheet.date:
            date_diff = abs((commit.commit_date.date() - timesheet.date).days)
            if date_diff == 0:
                reasons.append(_('Same date'))
            elif date_diff <= 1:
                reasons.append(_('1 day difference'))
            elif date_diff <= 7:
                reasons.append(_('%d days difference') % date_diff)
        
        # Confidence level
        if score >= 0.8:
            reasons.append(_('High confidence match'))
        elif score >= 0.6:
            reasons.append(_('Good confidence match'))
        elif score >= 0.4:
            reasons.append(_('Moderate confidence match'))
        
        return reasons
    
    def _validate_mapping_rules(self, commit, timesheet, raise_error=True):
        """Validate business rules for commit-timesheet mapping.
        
        Args:
            commit: git.commit record
            timesheet: account.analytic.line record
            raise_error: Whether to raise exceptions or return result
            
        Returns:
            dict: Validation result (if raise_error=False)
            
        Raises:
            ValidationError: If validation fails and raise_error=True
        """
        errors = []
        
        # Company consistency
        if commit.company_id != timesheet.company_id:
            errors.append(_(
                'Company mismatch: commit belongs to %s, timesheet belongs to %s'
            ) % (commit.company_id.name, timesheet.company_id.name))
        
        # User access rights
        try:
            timesheet.check_access_rights('write')
            timesheet.check_access_rule('write')
        except Exception:
            errors.append(_('Insufficient permissions to map to this timesheet'))
        
        # Project validation
        if not timesheet.project_id:
            errors.append(_('Timesheet must be associated with a project'))
        
        # Date validation (optional business rule)
        if commit.commit_date and timesheet.date:
            date_diff = abs((commit.commit_date.date() - timesheet.date).days)
            if date_diff > 30:  # Configurable threshold
                errors.append(_(
                    'Commit date (%s) is more than 30 days from timesheet date (%s)'
                ) % (commit.commit_date.date(), timesheet.date))
        
        if errors:
            if raise_error:
                raise ValidationError('\n'.join(errors))
            else:
                return {'valid': False, 'error': '\n'.join(errors)}
        
        return {'valid': True, 'error': None}
    
    @api.model
    def remove_mapping(self, mapping_id):
        """Remove a commit to timesheet mapping.
        
        Args:
            mapping_id: ID of timesheet.commit.mapping record
            
        Returns:
            dict: Result with success status
        """
        try:
            mapping = self.env['timesheet.commit.mapping'].browse(mapping_id)
            
            if not mapping.exists():
                raise ValidationError(_('Mapping not found'))
            
            # Check permissions
            if not self.env.user.has_group('git_timesheet_mapper.group_git_repository_admin'):
                if mapping.mapped_by != self.env.user:
                    raise ValidationError(_('You can only remove mappings you created'))
            
            commit_hash = mapping.commit_id.short_hash
            timesheet_name = mapping.timesheet_line_id.name
            
            mapping.unlink()
            
            return {
                'success': True,
                'message': _('Mapping removed: %s from %s') % (commit_hash, timesheet_name)
            }
            
        except Exception as e:
            _logger.error(f"Failed to remove mapping: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def get_mapping_statistics(self, filter_data=None):
        """Get comprehensive mapping statistics.
        
        Args:
            filter_data: Optional filters (project_id, user_id, date_from, date_to)
            
        Returns:
            dict: Mapping statistics and insights
        """
        try:
            filter_data = filter_data or {}
            
            # Build domain for filtering
            mapping_domain = []
            if filter_data.get('project_id'):
                mapping_domain.append(('project_id', '=', filter_data['project_id']))
            if filter_data.get('user_id'):
                mapping_domain.append(('timesheet_user_id', '=', filter_data['user_id']))
            if filter_data.get('date_from'):
                mapping_domain.append(('mapping_date', '>=', filter_data['date_from']))
            if filter_data.get('date_to'):
                mapping_domain.append(('mapping_date', '<=', filter_data['date_to']))
            
            mappings = self.env['timesheet.commit.mapping'].search(mapping_domain)
            
            # Calculate statistics
            total_mappings = len(mappings)
            unique_commits = len(set(mappings.mapped('commit_id.id')))
            unique_timesheets = len(set(mappings.mapped('timesheet_line_id.id')))
            unique_projects = len(set(mappings.mapped('project_id.id')))
            total_hours = sum(mappings.mapped('timesheet_hours'))
            
            # Mapping methods breakdown
            method_stats = {}
            for method, label in self.env['timesheet.commit.mapping']._fields['mapping_method'].selection:
                count = len(mappings.filtered(lambda m: m.mapping_method == method))
                method_stats[method] = {'count': count, 'label': label}
            
            # Top mappers
            mapper_stats = []
            for user in set(mappings.mapped('mapped_by')):
                user_mappings = mappings.filtered(lambda m: m.mapped_by == user)
                mapper_stats.append({
                    'user_id': user.id,
                    'user_name': user.name,
                    'mapping_count': len(user_mappings),
                    'hours_mapped': sum(user_mappings.mapped('timesheet_hours'))
                })
            mapper_stats.sort(key=lambda x: x['mapping_count'], reverse=True)
            
            # Project breakdown
            project_stats = []
            for project in set(mappings.mapped('project_id')):
                project_mappings = mappings.filtered(lambda m: m.project_id == project)
                project_stats.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'mapping_count': len(project_mappings),
                    'hours_mapped': sum(project_mappings.mapped('timesheet_hours')),
                    'commit_count': len(set(project_mappings.mapped('commit_id.id')))
                })
            project_stats.sort(key=lambda x: x['mapping_count'], reverse=True)
            
            return {
                'success': True,
                'statistics': {
                    'totals': {
                        'total_mappings': total_mappings,
                        'unique_commits': unique_commits,
                        'unique_timesheets': unique_timesheets,
                        'unique_projects': unique_projects,
                        'total_hours_mapped': total_hours
                    },
                    'methods': method_stats,
                    'top_mappers': mapper_stats[:10],
                    'project_breakdown': project_stats[:10]
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to get mapping statistics: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'statistics': {}
            }
    
    @api.model
    def auto_map_commits(self, repository_id=None, confidence_threshold=0.8):
        """Automatically create high-confidence mappings.
        
        Args:
            repository_id: Optional repository filter
            confidence_threshold: Minimum confidence score for auto-mapping
            
        Returns:
            dict: Auto-mapping results
        """
        try:
            # Get unmapped commits
            commit_domain = [('is_mapped', '=', False)]
            if repository_id:
                commit_domain.append(('repository_id', '=', repository_id))
            
            unmapped_commits = self.env['git.commit'].search(commit_domain)
            
            if not unmapped_commits:
                return {
                    'success': True,
                    'message': _('No unmapped commits found'),
                    'auto_mapped_count': 0,
                    'mappings': []
                }
            
            # Generate suggestions for all unmapped commits
            suggestions_result = self.suggest_mappings(
                commit_ids=unmapped_commits.ids,
                limit=1  # Only need top suggestion per commit
            )
            
            if not suggestions_result['success']:
                return suggestions_result
            
            auto_mappings = suggestions_result['suggestions']['auto_mappings']
            
            # Filter by confidence threshold
            high_confidence_mappings = [
                mapping for mapping in auto_mappings 
                if mapping['confidence_score'] >= confidence_threshold
            ]
            
            # Create automatic mappings
            created_mappings = []
            failed_mappings = []
            
            for mapping_suggestion in high_confidence_mappings:
                try:
                    result = self.create_mapping(
                        commit_id=mapping_suggestion['commit_id'],
                        timesheet_line_id=mapping_suggestion['timesheet_id'],
                        description=f"Auto-mapped (confidence: {mapping_suggestion['confidence_score']:.2f})"
                    )
                    
                    if result['success']:
                        created_mappings.append({
                            'mapping_id': result['mapping_id'],
                            'commit_id': mapping_suggestion['commit_id'],
                            'timesheet_id': mapping_suggestion['timesheet_id'],
                            'confidence_score': mapping_suggestion['confidence_score'],
                            'reasons': mapping_suggestion['reasons']
                        })
                    else:
                        failed_mappings.append({
                            'commit_id': mapping_suggestion['commit_id'],
                            'error': result['error']
                        })
                        
                except Exception as e:
                    failed_mappings.append({
                        'commit_id': mapping_suggestion['commit_id'],
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'auto_mapped_count': len(created_mappings),
                'failed_count': len(failed_mappings),
                'mappings': created_mappings,
                'failed_mappings': failed_mappings,
                'message': _(
                    'Auto-mapping completed: %d mappings created, %d failed'
                ) % (len(created_mappings), len(failed_mappings))
            }
            
        except Exception as e:
            _logger.error(f"Auto-mapping failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'auto_mapped_count': 0
            }
