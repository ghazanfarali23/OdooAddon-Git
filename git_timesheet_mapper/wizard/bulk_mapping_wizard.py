# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BulkMappingWizard(models.TransientModel):
    """Wizard for bulk mapping Git commits to timesheet entries.
    
    This wizard provides a multi-step interface for users to:
    1. Select commits for mapping
    2. Choose target timesheet entries
    3. Preview and confirm mappings
    4. Execute bulk mapping operations
    """
    _name = 'bulk.mapping.wizard'
    _description = 'Bulk Commit Mapping Wizard'

    # Wizard State Management
    state = fields.Selection([
        ('select_commits', 'Select Commits'),
        ('select_timesheet', 'Select Timesheet'),
        ('preview', 'Preview Mappings'),
        ('processing', 'Processing'),
        ('complete', 'Complete')
    ], string='State', default='select_commits', required=True)
    
    wizard_title = fields.Char(
        string='Title',
        compute='_compute_wizard_title',
        store=False
    )
    
    progress_percentage = fields.Float(
        string='Progress',
        compute='_compute_progress',
        store=False
    )
    
    # Step 1: Commit Selection
    repository_id = fields.Many2one(
        'git.repository',
        string='Repository',
        required=True,
        domain=[('connection_status', '=', 'connected')]
    )
    
    branch_name = fields.Selection(
        string='Branch',
        selection='_get_branch_selection',
        help='Filter commits by branch'
    )
    
    commit_date_from = fields.Date(
        string='From Date',
        default=lambda self: fields.Date.today() - timedelta(days=30),
        help='Filter commits from this date'
    )
    
    commit_date_to = fields.Date(
        string='To Date',
        default=fields.Date.today,
        help='Filter commits until this date'
    )
    
    commit_author = fields.Char(
        string='Author',
        help='Filter commits by author name or email'
    )
    
    commit_type = fields.Selection([
        ('feature', 'Feature'),
        ('bugfix', 'Bug Fix'),
        ('refactor', 'Refactor'),
        ('docs', 'Documentation'),
        ('test', 'Test'),
        ('chore', 'Chore'),
        ('other', 'Other')
    ], string='Commit Type', help='Filter commits by type')
    
    only_unmapped = fields.Boolean(
        string='Only Unmapped Commits',
        default=True,
        help='Show only commits that are not yet mapped'
    )
    
    selected_commit_ids = fields.Many2many(
        'git.commit',
        'wizard_commit_rel',
        'wizard_id',
        'commit_id',
        string='Selected Commits'
    )
    
    available_commit_ids = fields.Many2many(
        'git.commit',
        'wizard_available_commit_rel',
        'wizard_id',
        'commit_id',
        string='Available Commits',
        compute='_compute_available_commits',
        store=False
    )
    
    commit_count = fields.Integer(
        string='Available Commits',
        compute='_compute_commit_count',
        store=False
    )
    
    selected_commit_count = fields.Integer(
        string='Selected Commits',
        compute='_compute_selected_commit_count',
        store=False
    )
    
    # Step 2: Timesheet Selection
    timesheet_selection_mode = fields.Selection([
        ('single', 'Single Timesheet Entry'),
        ('project', 'All Entries in Project'),
        ('task', 'All Entries in Task'),
        ('employee', 'All Entries by Employee')
    ], string='Selection Mode', default='single', required=True)
    
    target_timesheet_id = fields.Many2one(
        'account.analytic.line',
        string='Target Timesheet',
        domain=[('project_id', '!=', False)]
    )
    
    target_project_id = fields.Many2one(
        'project.project',
        string='Target Project'
    )
    
    target_task_id = fields.Many2one(
        'project.task',
        string='Target Task',
        domain="[('project_id', '=', target_project_id)]"
    )
    
    target_employee_id = fields.Many2one(
        'hr.employee',
        string='Target Employee'
    )
    
    timesheet_date_from = fields.Date(
        string='Timesheet From Date',
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    
    timesheet_date_to = fields.Date(
        string='Timesheet To Date',
        default=fields.Date.today
    )
    
    target_timesheet_ids = fields.Many2many(
        'account.analytic.line',
        'wizard_timesheet_rel',
        'wizard_id',
        'timesheet_id',
        string='Target Timesheets',
        compute='_compute_target_timesheets',
        store=False
    )
    
    # Step 3: Preview and Configuration
    mapping_method = fields.Selection([
        ('manual', 'Manual'),
        ('bulk', 'Bulk'),
        ('automatic', 'Automatic')
    ], string='Mapping Method', default='bulk', required=True)
    
    mapping_description = fields.Text(
        string='Description',
        help='Optional description for all mappings'
    )
    
    auto_verify = fields.Boolean(
        string='Auto-verify Mappings',
        default=False,
        help='Automatically mark mappings as verified'
    )
    
    preview_mapping_ids = fields.One2many(
        'bulk.mapping.preview',
        'wizard_id',
        string='Preview Mappings',
        compute='_compute_preview_mappings',
        store=False
    )
    
    # Step 4: Processing Results
    processing_status = fields.Text(
        string='Processing Status',
        readonly=True
    )
    
    mappings_created = fields.Integer(
        string='Mappings Created',
        readonly=True,
        default=0
    )
    
    mappings_failed = fields.Integer(
        string='Mappings Failed',
        readonly=True,
        default=0
    )
    
    error_log = fields.Text(
        string='Error Log',
        readonly=True
    )
    
    # Computed Fields
    @api.depends('state')
    def _compute_wizard_title(self):
        """Compute dynamic wizard title based on current state."""
        titles = {
            'select_commits': _('Step 1: Select Commits'),
            'select_timesheet': _('Step 2: Select Timesheet Target'),
            'preview': _('Step 3: Preview Mappings'),
            'processing': _('Step 4: Processing Mappings'),
            'complete': _('Bulk Mapping Complete')
        }
        for wizard in self:
            wizard.wizard_title = titles.get(wizard.state, _('Bulk Mapping Wizard'))
    
    @api.depends('state', 'selected_commit_count', 'mappings_created', 'mappings_failed')
    def _compute_progress(self):
        """Compute progress percentage based on current state."""
        for wizard in self:
            if wizard.state == 'select_commits':
                wizard.progress_percentage = 20.0
            elif wizard.state == 'select_timesheet':
                wizard.progress_percentage = 40.0
            elif wizard.state == 'preview':
                wizard.progress_percentage = 60.0
            elif wizard.state == 'processing':
                if wizard.selected_commit_count > 0:
                    completed = wizard.mappings_created + wizard.mappings_failed
                    wizard.progress_percentage = 60.0 + (completed / wizard.selected_commit_count * 30.0)
                else:
                    wizard.progress_percentage = 80.0
            elif wizard.state == 'complete':
                wizard.progress_percentage = 100.0
            else:
                wizard.progress_percentage = 0.0
    
    @api.depends('repository_id', 'branch_name', 'commit_date_from', 'commit_date_to', 
                 'commit_author', 'commit_type', 'only_unmapped')
    def _compute_available_commits(self):
        """Compute available commits based on filter criteria."""
        for wizard in self:
            if not wizard.repository_id:
                wizard.available_commit_ids = [(6, 0, [])]
                continue
            
            domain = [('repository_id', '=', wizard.repository_id.id)]
            
            if wizard.branch_name:
                domain.append(('branch_name', '=', wizard.branch_name))
            
            if wizard.commit_date_from:
                domain.append(('commit_date', '>=', wizard.commit_date_from))
            
            if wizard.commit_date_to:
                domain.append(('commit_date', '<=', wizard.commit_date_to))
            
            if wizard.commit_author:
                domain.extend(['|', 
                              ('author_name', 'ilike', wizard.commit_author),
                              ('author_email', 'ilike', wizard.commit_author)])
            
            if wizard.commit_type:
                domain.append(('commit_type', '=', wizard.commit_type))
            
            if wizard.only_unmapped:
                domain.append(('is_mapped', '=', False))
            
            commits = self.env['git.commit'].search(domain, limit=1000, order='commit_date desc')
            wizard.available_commit_ids = [(6, 0, commits.ids)]
    
    @api.depends('available_commit_ids')
    def _compute_commit_count(self):
        """Compute number of available commits."""
        for wizard in self:
            wizard.commit_count = len(wizard.available_commit_ids)
    
    @api.depends('selected_commit_ids')
    def _compute_selected_commit_count(self):
        """Compute number of selected commits."""
        for wizard in self:
            wizard.selected_commit_count = len(wizard.selected_commit_ids)
    
    @api.depends('timesheet_selection_mode', 'target_timesheet_id', 'target_project_id',
                 'target_task_id', 'target_employee_id', 'timesheet_date_from', 'timesheet_date_to')
    def _compute_target_timesheets(self):
        """Compute target timesheet entries based on selection mode."""
        for wizard in self:
            domain = [('project_id', '!=', False)]
            
            if wizard.timesheet_date_from:
                domain.append(('date', '>=', wizard.timesheet_date_from))
            
            if wizard.timesheet_date_to:
                domain.append(('date', '<=', wizard.timesheet_date_to))
            
            if wizard.timesheet_selection_mode == 'single':
                if wizard.target_timesheet_id:
                    wizard.target_timesheet_ids = [(6, 0, [wizard.target_timesheet_id.id])]
                else:
                    wizard.target_timesheet_ids = [(6, 0, [])]
            
            elif wizard.timesheet_selection_mode == 'project':
                if wizard.target_project_id:
                    domain.append(('project_id', '=', wizard.target_project_id.id))
                    timesheets = self.env['account.analytic.line'].search(domain)
                    wizard.target_timesheet_ids = [(6, 0, timesheets.ids)]
                else:
                    wizard.target_timesheet_ids = [(6, 0, [])]
            
            elif wizard.timesheet_selection_mode == 'task':
                if wizard.target_task_id:
                    domain.append(('task_id', '=', wizard.target_task_id.id))
                    timesheets = self.env['account.analytic.line'].search(domain)
                    wizard.target_timesheet_ids = [(6, 0, timesheets.ids)]
                else:
                    wizard.target_timesheet_ids = [(6, 0, [])]
            
            elif wizard.timesheet_selection_mode == 'employee':
                if wizard.target_employee_id:
                    domain.append(('employee_id', '=', wizard.target_employee_id.id))
                    timesheets = self.env['account.analytic.line'].search(domain)
                    wizard.target_timesheet_ids = [(6, 0, timesheets.ids)]
                else:
                    wizard.target_timesheet_ids = [(6, 0, [])]
    
    @api.depends('selected_commit_ids', 'target_timesheet_ids', 'mapping_method')
    def _compute_preview_mappings(self):
        """Compute preview of mappings to be created."""
        for wizard in self:
            preview_lines = []
            
            if wizard.selected_commit_ids and wizard.target_timesheet_ids:
                # Simple 1:1 mapping for preview (can be enhanced with smart matching)
                for i, commit in enumerate(wizard.selected_commit_ids):
                    timesheet_index = i % len(wizard.target_timesheet_ids)
                    timesheet = wizard.target_timesheet_ids[timesheet_index]
                    
                    preview_lines.append((0, 0, {
                        'commit_id': commit.id,
                        'timesheet_id': timesheet.id,
                        'confidence_score': self._calculate_confidence_score(commit, timesheet),
                        'mapping_method': wizard.mapping_method,
                    }))
            
            wizard.preview_mapping_ids = preview_lines
    
    # Selection Methods
    def _get_branch_selection(self):
        """Get available branches for selected repository."""
        if not self.repository_id:
            return []
        
        branches = self.env['git.commit'].search([
            ('repository_id', '=', self.repository_id.id)
        ]).mapped('branch_name')
        
        return [(branch, branch) for branch in sorted(set(branches)) if branch]
    
    # Navigation Methods
    def action_next_step(self):
        """Navigate to next wizard step."""
        self.ensure_one()
        
        if self.state == 'select_commits':
            if not self.selected_commit_ids:
                raise ValidationError(_('Please select at least one commit.'))
            self.state = 'select_timesheet'
        
        elif self.state == 'select_timesheet':
            if not self.target_timesheet_ids:
                raise ValidationError(_('Please select target timesheet entries.'))
            self.state = 'preview'
        
        elif self.state == 'preview':
            self.state = 'processing'
            return self.action_process_mappings()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_previous_step(self):
        """Navigate to previous wizard step."""
        self.ensure_one()
        
        if self.state == 'select_timesheet':
            self.state = 'select_commits'
        elif self.state == 'preview':
            self.state = 'select_timesheet'
        elif self.state == 'complete':
            self.state = 'preview'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_select_all_commits(self):
        """Select all available commits."""
        self.ensure_one()
        self.selected_commit_ids = [(6, 0, self.available_commit_ids.ids)]
    
    def action_deselect_all_commits(self):
        """Deselect all commits."""
        self.ensure_one()
        self.selected_commit_ids = [(6, 0, [])]
    
    def action_refresh_commits(self):
        """Refresh available commits based on current filters."""
        self.ensure_one()
        self._compute_available_commits()
    
    # Processing Methods
    def action_process_mappings(self):
        """Process the bulk mapping operation."""
        self.ensure_one()
        
        try:
            self.processing_status = _('Starting bulk mapping process...')
            self.mappings_created = 0
            self.mappings_failed = 0
            
            mapping_service = self.env['mapping.service']
            
            # Process mappings
            for i, commit in enumerate(self.selected_commit_ids):
                try:
                    # Select target timesheet (can be enhanced with smart matching)
                    timesheet_index = i % len(self.target_timesheet_ids)
                    timesheet = self.target_timesheet_ids[timesheet_index]
                    
                    self.processing_status = _(
                        'Processing mapping %d of %d: %s -> %s'
                    ) % (i + 1, len(self.selected_commit_ids), 
                         commit.short_hash, timesheet.name)
                    
                    # Create mapping
                    result = mapping_service.create_mapping(
                        commit_id=commit.id,
                        timesheet_line_id=timesheet.id,
                        description=self.mapping_description,
                        mapping_method=self.mapping_method,
                        auto_verify=self.auto_verify
                    )
                    
                    if result['success']:
                        self.mappings_created += 1
                    else:
                        self.mappings_failed += 1
                        self._log_error(commit, timesheet, result['error'])
                
                except Exception as e:
                    self.mappings_failed += 1
                    self._log_error(commit, None, str(e))
                    _logger.error(f"Bulk mapping error for commit {commit.commit_hash}: {str(e)}")
            
            self.processing_status = _(
                'Bulk mapping complete. Created: %d, Failed: %d'
            ) % (self.mappings_created, self.mappings_failed)
            
            self.state = 'complete'
            
        except Exception as e:
            self.processing_status = _('Error during bulk mapping: %s') % str(e)
            self.state = 'complete'
            _logger.error(f"Bulk mapping wizard error: {str(e)}")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_view_created_mappings(self):
        """View the created mappings."""
        self.ensure_one()
        
        # Find mappings created by this wizard
        mappings = self.env['timesheet.commit.mapping'].search([
            ('commit_id', 'in', self.selected_commit_ids.ids),
            ('mapping_method', '=', self.mapping_method),
            ('create_date', '>=', self.create_date)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Mappings'),
            'res_model': 'timesheet.commit.mapping',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', mappings.ids)],
            'target': 'current',
        }
    
    # Utility Methods
    def _calculate_confidence_score(self, commit, timesheet):
        """Calculate confidence score for a commit-timesheet mapping."""
        score = 50.0  # Base score
        
        # Date proximity
        if commit.commit_date and timesheet.date:
            date_diff = abs((commit.commit_date.date() - timesheet.date).days)
            if date_diff <= 1:
                score += 30.0
            elif date_diff <= 7:
                score += 20.0
            elif date_diff <= 30:
                score += 10.0
        
        # Author matching
        if timesheet.employee_id and commit.author_email:
            employee_email = timesheet.employee_id.work_email
            if employee_email and employee_email.lower() == commit.author_email.lower():
                score += 20.0
        
        return min(score, 100.0)
    
    def _log_error(self, commit, timesheet, error_message):
        """Log error for failed mapping."""
        error_line = _('Commit %s') % (commit.short_hash if commit else 'Unknown')
        if timesheet:
            error_line += _(' -> Timesheet %s') % timesheet.name
        error_line += _(': %s\n') % error_message
        
        if self.error_log:
            self.error_log += error_line
        else:
            self.error_log = error_line


class BulkMappingPreview(models.TransientModel):
    """Preview line for bulk mapping wizard."""
    _name = 'bulk.mapping.preview'
    _description = 'Bulk Mapping Preview Line'
    
    wizard_id = fields.Many2one('bulk.mapping.wizard', string='Wizard', required=True, ondelete='cascade')
    commit_id = fields.Many2one('git.commit', string='Commit', required=True)
    timesheet_id = fields.Many2one('account.analytic.line', string='Timesheet', required=True)
    confidence_score = fields.Float(string='Confidence', default=50.0)
    mapping_method = fields.Selection([
        ('manual', 'Manual'),
        ('bulk', 'Bulk'),
        ('automatic', 'Automatic')
    ], string='Method', default='bulk')
    
    # Display fields
    commit_hash = fields.Char(related='commit_id.short_hash', string='Hash')
    commit_message = fields.Char(related='commit_id.commit_message_short', string='Message')
    commit_author = fields.Char(related='commit_id.author_name', string='Author')
    timesheet_name = fields.Char(related='timesheet_id.name', string='Timesheet')
    project_name = fields.Char(related='timesheet_id.project_id.name', string='Project')
    task_name = fields.Char(related='timesheet_id.task_id.name', string='Task')
