# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class TimesheetCommitMapping(models.Model):
    """Mapping between Git Commits and Timesheet entries.
    
    This model creates the many-to-many relationship between git.commit
    and account.analytic.line (timesheet entries), allowing users to
    map commits to specific timesheet entries for tracking purposes.
    """
    
    _name = 'timesheet.commit.mapping'
    _description = 'Timesheet Commit Mapping'
    _rec_name = 'display_name'
    _order = 'mapping_date desc'
    
    # Core Relationship
    commit_id = fields.Many2one(
        'git.commit',
        string='Commit',
        required=True,
        ondelete='cascade',
        help='Git commit being mapped'
    )
    
    timesheet_line_id = fields.Many2one(
        'account.analytic.line',
        string='Timesheet Entry',
        required=True,
        ondelete='cascade',
        domain=[('project_id', '!=', False)],
        help='Timesheet entry this commit is mapped to'
    )
    
    # Mapping Metadata
    mapped_by = fields.Many2one(
        'res.users',
        string='Mapped By',
        required=True,
        default=lambda self: self.env.user,
        help='User who created this mapping'
    )
    
    mapping_date = fields.Datetime(
        string='Mapping Date',
        required=True,
        default=fields.Datetime.now,
        help='When this mapping was created'
    )
    
    mapping_method = fields.Selection([
        ('manual', 'Manual'),
        ('bulk', 'Bulk Operation'),
        ('automatic', 'Automatic'),
        ('import', 'Import')
    ], string='Mapping Method', required=True, default='manual')
    
    # Additional Information
    description = fields.Text(
        string='Mapping Description',
        help='Optional description for this mapping'
    )
    
    confidence_score = fields.Float(
        string='Confidence Score',
        help='Confidence score for automatic mappings (0.0 to 1.0)'
    )
    
    # Related Fields for Easy Access
    commit_hash = fields.Char(
        string='Commit Hash',
        related='commit_id.commit_hash',
        store=True
    )
    
    commit_message = fields.Text(
        string='Commit Message',
        related='commit_id.commit_message',
        store=True
    )
    
    commit_author = fields.Char(
        string='Commit Author',
        related='commit_id.author_name',
        store=True
    )
    
    commit_date = fields.Datetime(
        string='Commit Date',
        related='commit_id.commit_date',
        store=True
    )
    
    repository_id = fields.Many2one(
        'git.repository',
        string='Repository',
        related='commit_id.repository_id',
        store=True
    )
    
    # Timesheet Related Fields
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='timesheet_line_id.project_id',
        store=True
    )
    
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        related='timesheet_line_id.task_id',
        store=True
    )
    
    timesheet_user_id = fields.Many2one(
        'res.users',
        string='Timesheet User',
        related='timesheet_line_id.user_id',
        store=True
    )
    
    timesheet_date = fields.Date(
        string='Timesheet Date',
        related='timesheet_line_id.date',
        store=True
    )
    
    timesheet_hours = fields.Float(
        string='Hours Logged',
        related='timesheet_line_id.unit_amount',
        store=True
    )
    
    # Display and Navigation
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        help='User-friendly display name'
    )
    
    # Status and Validation
    is_valid = fields.Boolean(
        string='Is Valid',
        compute='_compute_is_valid',
        store=True,
        help='Whether this mapping is still valid'
    )
    
    validation_errors = fields.Text(
        string='Validation Errors',
        compute='_compute_is_valid',
        store=True,
        help='Any validation errors for this mapping'
    )
    
    # Audit Trail
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='timesheet_line_id.company_id',
        store=True
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_commit_timesheet',
         'UNIQUE(commit_id, timesheet_line_id)',
         'A commit can only be mapped once to the same timesheet entry!')
    ]
    
    @api.depends('commit_id.short_hash', 'timesheet_line_id.name', 'project_id.name')
    def _compute_display_name(self):
        """Compute user-friendly display name."""
        for record in self:
            if record.commit_id and record.timesheet_line_id:
                commit_info = record.commit_id.short_hash or 'New Commit'
                timesheet_info = record.timesheet_line_id.name or 'Timesheet Entry'
                project_info = record.project_id.name if record.project_id else 'No Project'
                record.display_name = f"{commit_info} → {timesheet_info} ({project_info})"
            else:
                record.display_name = 'New Mapping'
    
    @api.depends('commit_id', 'timesheet_line_id', 'company_id')
    def _compute_is_valid(self):
        """Validate mapping and identify any issues."""
        for record in self:
            errors = []
            is_valid = True
            
            # Check if commit still exists and is accessible
            if not record.commit_id or not record.commit_id.active:
                errors.append('Commit no longer exists or is inactive')
                is_valid = False
            
            # Check if timesheet still exists and is accessible
            if not record.timesheet_line_id or not record.timesheet_line_id.active:
                errors.append('Timesheet entry no longer exists or is inactive')
                is_valid = False
            
            # Check company consistency
            if (record.commit_id and record.timesheet_line_id and 
                record.commit_id.company_id != record.timesheet_line_id.company_id):
                errors.append('Company mismatch between commit and timesheet')
                is_valid = False
            
            # Check if user has access to timesheet
            if (record.timesheet_line_id and 
                not self.env['account.analytic.line'].check_access_rights('read', raise_exception=False)):
                errors.append('No access to timesheet entry')
                is_valid = False
            
            record.is_valid = is_valid
            record.validation_errors = '\n'.join(errors) if errors else False
    
    @api.constrains('commit_id', 'timesheet_line_id')
    def _check_commit_not_already_mapped(self):
        """Validate that commit is not already mapped to another timesheet."""
        for record in self:
            if record.commit_id and record.timesheet_line_id:
                # Check for existing mappings to different timesheets
                existing_mappings = self.search([
                    ('commit_id', '=', record.commit_id.id),
                    ('timesheet_line_id', '!=', record.timesheet_line_id.id),
                    ('id', '!=', record.id)
                ])
                
                if existing_mappings:
                    raise ValidationError(_(
                        'Commit %s is already mapped to a different timesheet entry. '
                        'Each commit can only be mapped to one timesheet entry.'
                    ) % record.commit_id.short_hash)
    
    @api.constrains('timesheet_line_id')
    def _check_timesheet_access(self):
        """Validate user has access to the timesheet entry."""
        for record in self:
            if record.timesheet_line_id:
                # Check if user can access this timesheet entry
                try:
                    record.timesheet_line_id.check_access_rights('read')
                    record.timesheet_line_id.check_access_rule('read')
                except Exception:
                    raise ValidationError(_(
                        'You do not have access to map commits to this timesheet entry.'
                    ))
    
    @api.constrains('commit_id', 'timesheet_line_id', 'company_id')
    def _check_company_consistency(self):
        """Validate company consistency between commit and timesheet."""
        for record in self:
            if (record.commit_id and record.timesheet_line_id and 
                record.commit_id.company_id != record.timesheet_line_id.company_id):
                raise ValidationError(_(
                    'Cannot map commit from company %s to timesheet from company %s. '
                    'Commits can only be mapped to timesheets within the same company.'
                ) % (record.commit_id.company_id.name, record.timesheet_line_id.company_id.name))
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to update commit mapping status."""
        mappings = super().create(vals_list)
        
        # Mark commits as mapped
        for mapping in mappings:
            if mapping.commit_id:
                mapping.commit_id.mark_as_mapped(mapping.mapped_by)
        
        return mappings
    
    def unlink(self):
        """Override unlink to update commit mapping status."""
        commits_to_check = self.mapped('commit_id')
        
        result = super().unlink()
        
        # Check if commits should be marked as unmapped
        for commit in commits_to_check:
            if commit.exists():
                commit.mark_as_unmapped()
        
        return result
    
    def action_view_commit(self):
        """View the associated commit."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commit Details'),
            'res_model': 'git.commit',
            'res_id': self.commit_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def action_view_timesheet(self):
        """View the associated timesheet entry."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheet Entry'),
            'res_model': 'account.analytic.line',
            'res_id': self.timesheet_line_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def action_open_commit_url(self):
        """Open commit URL in browser."""
        self.ensure_one()
        
        return self.commit_id.action_open_commit_url()
    
    @api.model
    def get_mapping_statistics(self, project_id=None, user_id=None, date_from=None, date_to=None):
        """Get mapping statistics.
        
        Args:
            project_id: Optional project filter
            user_id: Optional user filter
            date_from: Optional start date
            date_to: Optional end date
            
        Returns:
            dict: Statistics data
        """
        domain = []
        
        if project_id:
            domain.append(('project_id', '=', project_id))
        
        if user_id:
            domain.append(('timesheet_user_id', '=', user_id))
        
        if date_from:
            domain.append(('mapping_date', '>=', date_from))
        
        if date_to:
            domain.append(('mapping_date', '<=', date_to))
        
        mappings = self.search(domain)
        
        return {
            'total_mappings': len(mappings),
            'unique_commits': len(set(mappings.mapped('commit_id.id'))),
            'unique_timesheets': len(set(mappings.mapped('timesheet_line_id.id'))),
            'unique_projects': len(set(mappings.mapped('project_id.id'))),
            'total_hours_mapped': sum(mappings.mapped('timesheet_hours')),
            'mapping_methods': {
                method: len(mappings.filtered(lambda m: m.mapping_method == method))
                for method in dict(self._fields['mapping_method'].selection).keys()
            },
            'top_mappers': [
                (user.name, len(mappings.filtered(lambda m: m.mapped_by == user)))
                for user in set(mappings.mapped('mapped_by'))
            ]
        }
    
    @api.model
    def bulk_create_mappings(self, commit_ids, timesheet_line_id, description=None):
        """Create multiple mappings at once.
        
        Args:
            commit_ids: List of commit IDs to map
            timesheet_line_id: Target timesheet entry ID
            description: Optional description for all mappings
            
        Returns:
            dict: Result with created mappings and any errors
        """
        created_mappings = []
        failed_mappings = []
        
        for commit_id in commit_ids:
            try:
                # Check if commit is already mapped
                existing_mapping = self.search([
                    ('commit_id', '=', commit_id)
                ])
                
                if existing_mapping:
                    failed_mappings.append({
                        'commit_id': commit_id,
                        'error': 'Commit already mapped'
                    })
                    continue
                
                # Create mapping
                mapping_data = {
                    'commit_id': commit_id,
                    'timesheet_line_id': timesheet_line_id,
                    'mapping_method': 'bulk',
                    'description': description or 'Bulk mapping operation'
                }
                
                mapping = self.create(mapping_data)
                created_mappings.append(mapping)
                
            except Exception as e:
                failed_mappings.append({
                    'commit_id': commit_id,
                    'error': str(e)
                })
        
        return {
            'created_mappings': len(created_mappings),
            'failed_mappings': len(failed_mappings),
            'mapping_ids': [m.id for m in created_mappings],
            'errors': failed_mappings
        }
    
    @api.model
    def suggest_mappings(self, commit_ids, limit=10):
        """Suggest potential timesheet mappings for commits.
        
        Args:
            commit_ids: List of commit IDs to suggest mappings for
            limit: Maximum number of suggestions per commit
            
        Returns:
            dict: Mapping suggestions with confidence scores
        """
        suggestions = {}
        
        for commit_id in commit_ids:
            commit = self.env['git.commit'].browse(commit_id)
            if not commit.exists():
                continue
            
            # Find potential timesheet entries based on:
            # 1. Same project (if repository is linked to project)
            # 2. Commit date proximity to timesheet date
            # 3. Author email matching user email
            # 4. Commit message keywords matching timesheet description
            
            timesheet_domain = [
                ('project_id', '!=', False),
                ('company_id', '=', commit.company_id.id)
            ]
            
            # Filter by project if repository is linked
            if commit.repository_id.project_id:
                timesheet_domain.append(('project_id', '=', commit.repository_id.project_id.id))
            
            # Filter by date range (within 7 days of commit)
            if commit.commit_date:
                date_from = commit.commit_date.date() - timedelta(days=7)
                date_to = commit.commit_date.date() + timedelta(days=7)
                timesheet_domain.extend([
                    ('date', '>=', date_from),
                    ('date', '<=', date_to)
                ])
            
            potential_timesheets = self.env['account.analytic.line'].search(timesheet_domain)
            
            # Score each potential timesheet
            scored_suggestions = []
            for timesheet in potential_timesheets[:limit]:
                score = self._calculate_mapping_score(commit, timesheet)
                if score > 0.3:  # Minimum confidence threshold
                    scored_suggestions.append({
                        'timesheet_id': timesheet.id,
                        'timesheet_name': timesheet.name,
                        'project_name': timesheet.project_id.name,
                        'task_name': timesheet.task_id.name if timesheet.task_id else '',
                        'confidence_score': score,
                        'reasons': self._get_mapping_reasons(commit, timesheet, score)
                    })
            
            # Sort by confidence score
            scored_suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)
            suggestions[commit_id] = scored_suggestions[:limit]
        
        return suggestions
    
    def _calculate_mapping_score(self, commit, timesheet):
        """Calculate confidence score for commit-timesheet mapping.
        
        Args:
            commit: git.commit record
            timesheet: account.analytic.line record
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        score = 0.0
        
        # Project match (highest weight)
        if (commit.repository_id.project_id and 
            commit.repository_id.project_id == timesheet.project_id):
            score += 0.4
        
        # Author email match
        if (commit.author_email and timesheet.user_id.email and 
            commit.author_email.lower() == timesheet.user_id.email.lower()):
            score += 0.3
        
        # Date proximity (within same day gets highest score)
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
        
        # Keyword matching in commit message and timesheet description
        if commit.commit_message and timesheet.name:
            commit_words = set(commit.commit_message.lower().split())
            timesheet_words = set(timesheet.name.lower().split())
            common_words = commit_words.intersection(timesheet_words)
            
            if common_words:
                score += min(0.1, len(common_words) * 0.02)
        
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
        
        if (commit.repository_id.project_id and 
            commit.repository_id.project_id == timesheet.project_id):
            reasons.append('Same project')
        
        if (commit.author_email and timesheet.user_id.email and 
            commit.author_email.lower() == timesheet.user_id.email.lower()):
            reasons.append('Author email matches timesheet user')
        
        if commit.commit_date and timesheet.date:
            date_diff = abs((commit.commit_date.date() - timesheet.date).days)
            if date_diff == 0:
                reasons.append('Same date')
            elif date_diff <= 1:
                reasons.append('Similar date (1 day)')
            elif date_diff <= 7:
                reasons.append(f'Close date ({date_diff} days)')
        
        if score > 0.8:
            reasons.append('High confidence match')
        elif score > 0.6:
            reasons.append('Good confidence match')
        
        return reasons


class AccountAnalyticLineExtension(models.Model):
    """Extension of account.analytic.line to add commit-related functionality."""
    
    _inherit = 'account.analytic.line'
    
    # Commit Relationship
    commit_mapping_ids = fields.One2many(
        'timesheet.commit.mapping',
        'timesheet_line_id',
        string='Commit Mappings',
        help='Git commits mapped to this timesheet entry'
    )
    
    # Computed Fields
    commit_count = fields.Integer(
        string='Commit Count',
        compute='_compute_commit_stats',
        help='Number of commits mapped to this timesheet'
    )
    
    has_commits = fields.Boolean(
        string='Has Commits',
        compute='_compute_commit_stats',
        help='Whether this timesheet has any mapped commits'
    )
    
    latest_commit_date = fields.Datetime(
        string='Latest Commit Date',
        compute='_compute_commit_stats',
        help='Date of the most recent mapped commit'
    )
    
    commit_authors = fields.Char(
        string='Commit Authors',
        compute='_compute_commit_stats',
        help='Comma-separated list of commit authors'
    )
    
    total_code_changes = fields.Integer(
        string='Total Code Changes',
        compute='_compute_commit_stats',
        help='Total lines changed across all mapped commits'
    )
    
    @api.depends('commit_mapping_ids')
    def _compute_commit_stats(self):
        """Compute commit-related statistics."""
        for record in self:
            mappings = record.commit_mapping_ids
            commits = mappings.mapped('commit_id')
            
            record.commit_count = len(commits)
            record.has_commits = bool(commits)
            
            if commits:
                # Latest commit date
                latest_commit = commits.sorted('commit_date', reverse=True)[0]
                record.latest_commit_date = latest_commit.commit_date
                
                # Unique authors
                authors = list(set(commits.mapped('author_name')))
                record.commit_authors = ', '.join(authors[:3])  # Show first 3 authors
                if len(authors) > 3:
                    record.commit_authors += f' (+{len(authors) - 3} more)'
                
                # Total code changes
                record.total_code_changes = sum(commits.mapped('total_changes'))
            else:
                record.latest_commit_date = False
                record.commit_authors = ''
                record.total_code_changes = 0
    
    def action_view_commits(self):
        """View mapped commits for this timesheet entry."""
        self.ensure_one()
        
        commit_ids = self.commit_mapping_ids.mapped('commit_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mapped Commits'),
            'res_model': 'git.commit',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', commit_ids)],
            'context': {'default_timesheet_line_id': self.id}
        }
    
    def action_map_commits(self):
        """Open wizard to map commits to this timesheet."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Map Commits'),
            'res_model': 'mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_timesheet_line_id': self.id,
                'default_project_id': self.project_id.id if self.project_id else False
            }
        }
