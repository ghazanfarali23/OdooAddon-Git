# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class GitCommit(models.Model):
    """Git Commit model for storing individual commit information.
    
    Stores commit metadata fetched from Git repositories and tracks
    mapping status to prevent duplicate mappings.
    """
    
    _name = 'git.commit'
    _description = 'Git Commit'
    _rec_name = 'commit_hash'
    _order = 'commit_date desc'
    
    # Repository Reference
    repository_id = fields.Many2one(
        'git.repository',
        string='Repository',
        required=True,
        ondelete='cascade',
        help='Repository this commit belongs to'
    )
    
    # Commit Identification
    commit_hash = fields.Char(
        string='Commit Hash',
        required=True,
        size=40,
        help='Full SHA hash of the commit'
    )
    
    short_hash = fields.Char(
        string='Short Hash',
        compute='_compute_short_hash',
        store=True,
        help='First 8 characters of commit hash'
    )
    
    # Commit Metadata
    author_name = fields.Char(
        string='Author Name',
        required=True,
        help='Name of the commit author'
    )
    
    author_email = fields.Char(
        string='Author Email',
        help='Email of the commit author'
    )
    
    committer_name = fields.Char(
        string='Committer Name',
        help='Name of the committer (if different from author)'
    )
    
    committer_email = fields.Char(
        string='Committer Email',
        help='Email of the committer (if different from author)'
    )
    
    # Commit Content
    commit_message = fields.Text(
        string='Commit Message',
        required=True,
        help='Full commit message'
    )
    
    commit_message_short = fields.Char(
        string='Short Message',
        compute='_compute_short_message',
        store=True,
        help='First line of commit message'
    )
    
    # Temporal Information
    commit_date = fields.Datetime(
        string='Commit Date',
        required=True,
        help='When the commit was made'
    )
    
    author_date = fields.Datetime(
        string='Author Date',
        help='When the changes were originally authored'
    )
    
    # Branch and Location
    branch_name = fields.Char(
        string='Branch',
        help='Branch where this commit was found'
    )
    
    # File Statistics
    files_changed = fields.Integer(
        string='Files Changed',
        help='Number of files modified in this commit'
    )
    
    lines_added = fields.Integer(
        string='Lines Added',
        help='Number of lines added'
    )
    
    lines_deleted = fields.Integer(
        string='Lines Deleted',
        help='Number of lines deleted'
    )
    
    total_changes = fields.Integer(
        string='Total Changes',
        compute='_compute_total_changes',
        store=True,
        help='Total lines added + deleted'
    )
    
    # Mapping Status
    is_mapped = fields.Boolean(
        string='Is Mapped',
        default=False,
        help='Whether this commit has been mapped to timesheet(s)'
    )
    
    mapping_count = fields.Integer(
        string='Mapping Count',
        compute='_compute_mapping_count',
        help='Number of timesheet mappings for this commit'
    )
    
    mapped_by = fields.Many2one(
        'res.users',
        string='Mapped By',
        help='User who mapped this commit'
    )
    
    mapping_date = fields.Datetime(
        string='Mapping Date',
        help='When this commit was first mapped'
    )
    
    # URLs and References
    commit_url = fields.Char(
        string='Commit URL',
        compute='_compute_commit_url',
        help='Direct URL to view this commit'
    )
    
    # Categorization
    commit_type = fields.Selection([
        ('feature', 'Feature'),
        ('bugfix', 'Bug Fix'),
        ('refactor', 'Refactoring'),
        ('docs', 'Documentation'),
        ('test', 'Testing'),
        ('chore', 'Chore'),
        ('other', 'Other')
    ], string='Commit Type', compute='_compute_commit_type', store=True)
    
    # Search and Display
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        help='User-friendly display name'
    )
    
    # Audit and Company
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='repository_id.company_id',
        store=True
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_commit_repository',
         'UNIQUE(commit_hash, repository_id)',
         'Commit hash must be unique per repository!')
    ]
    
    @api.depends('commit_hash')
    def _compute_short_hash(self):
        """Compute short hash (first 8 characters)."""
        for record in self:
            if record.commit_hash:
                record.short_hash = record.commit_hash[:8]
            else:
                record.short_hash = False
    
    @api.depends('commit_message')
    def _compute_short_message(self):
        """Compute short message (first line)."""
        for record in self:
            if record.commit_message:
                lines = record.commit_message.strip().split('\n')
                record.commit_message_short = lines[0][:100]
            else:
                record.commit_message_short = False
    
    @api.depends('lines_added', 'lines_deleted')
    def _compute_total_changes(self):
        """Compute total lines changed."""
        for record in self:
            record.total_changes = (record.lines_added or 0) + (record.lines_deleted or 0)
    
    @api.depends('commit_hash')
    def _compute_mapping_count(self):
        """Compute number of mappings."""
        for record in self:
            mappings = self.env['timesheet.commit.mapping'].search([
                ('commit_id', '=', record.id)
            ])
            record.mapping_count = len(mappings)
    
    @api.depends('repository_id.repository_url', 'commit_hash')
    def _compute_commit_url(self):
        """Compute direct URL to commit."""
        for record in self:
            if record.repository_id and record.commit_hash:
                base_url = record.repository_id.repository_url.rstrip('/')
                if 'github.com' in base_url:
                    record.commit_url = f"{base_url}/commit/{record.commit_hash}"
                elif 'gitlab.com' in base_url or '/gitlab' in base_url:
                    record.commit_url = f"{base_url}/-/commit/{record.commit_hash}"
                else:
                    record.commit_url = False
            else:
                record.commit_url = False
    
    @api.depends('commit_message')
    def _compute_commit_type(self):
        """Auto-categorize commit based on message."""
        for record in self:
            if record.commit_message:
                message_lower = record.commit_message.lower()
                
                # Check for conventional commit prefixes
                if any(prefix in message_lower for prefix in ['feat:', 'feature:']):
                    record.commit_type = 'feature'
                elif any(prefix in message_lower for prefix in ['fix:', 'bugfix:', 'bug:']):
                    record.commit_type = 'bugfix'
                elif any(prefix in message_lower for prefix in ['refactor:', 'refact:']):
                    record.commit_type = 'refactor'
                elif any(prefix in message_lower for prefix in ['docs:', 'doc:', 'documentation']):
                    record.commit_type = 'docs'
                elif any(prefix in message_lower for prefix in ['test:', 'tests:']):
                    record.commit_type = 'test'
                elif any(prefix in message_lower for prefix in ['chore:', 'style:', 'ci:']):
                    record.commit_type = 'chore'
                else:
                    record.commit_type = 'other'
            else:
                record.commit_type = 'other'
    
    @api.depends('short_hash', 'commit_message_short', 'author_name')
    def _compute_display_name(self):
        """Compute user-friendly display name."""
        for record in self:
            if record.short_hash and record.commit_message_short:
                record.display_name = f"{record.short_hash}: {record.commit_message_short}"
            elif record.short_hash:
                record.display_name = record.short_hash
            else:
                record.display_name = 'New Commit'
    
    @api.constrains('commit_hash')
    def _check_commit_hash(self):
        """Validate commit hash format."""
        for record in self:
            if record.commit_hash:
                # SHA-1 hash should be 40 hexadecimal characters
                import re
                if not re.match(r'^[a-f0-9]{40}$', record.commit_hash.lower()):
                    raise ValidationError(_(
                        'Invalid commit hash format. Must be 40 hexadecimal characters.'
                    ))
    
    @api.constrains('commit_date')
    def _check_commit_date(self):
        """Validate commit date is not in the future."""
        for record in self:
            if record.commit_date and record.commit_date > fields.Datetime.now():
                raise ValidationError(_(
                    'Commit date cannot be in the future.'
                ))
    
    def action_view_mappings(self):
        """View mappings for this commit."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commit Mappings'),
            'res_model': 'timesheet.commit.mapping',
            'view_mode': 'tree,form',
            'domain': [('commit_id', '=', self.id)],
            'context': {'default_commit_id': self.id}
        }
    
    def action_create_mapping(self):
        """Open wizard to create new mapping."""
        self.ensure_one()
        
        if self.is_mapped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('This commit is already mapped. Use bulk operations to modify mappings.'),
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Mapping'),
            'res_model': 'mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_commit_ids': [(6, 0, [self.id])],
                'default_repository_id': self.repository_id.id
            }
        }
    
    def action_open_commit_url(self):
        """Open commit URL in browser."""
        self.ensure_one()
        
        if not self.commit_url:
            raise ValidationError(_('No commit URL available'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': self.commit_url,
            'target': 'new'
        }
    
    def mark_as_mapped(self, mapped_by_user=None):
        """Mark commit as mapped.
        
        Args:
            mapped_by_user: User who performed the mapping
        """
        self.ensure_one()
        
        if not self.is_mapped:
            self.write({
                'is_mapped': True,
                'mapped_by': mapped_by_user.id if mapped_by_user else self.env.user.id,
                'mapping_date': fields.Datetime.now()
            })
    
    def mark_as_unmapped(self):
        """Mark commit as unmapped (when all mappings are removed)."""
        self.ensure_one()
        
        # Check if there are still active mappings
        active_mappings = self.env['timesheet.commit.mapping'].search([
            ('commit_id', '=', self.id)
        ])
        
        if not active_mappings:
            self.write({
                'is_mapped': False,
                'mapped_by': False,
                'mapping_date': False
            })
    
    def get_related_timesheets(self):
        """Get all timesheets this commit is mapped to.
        
        Returns:
            recordset: account.analytic.line records
        """
        self.ensure_one()
        
        mappings = self.env['timesheet.commit.mapping'].search([
            ('commit_id', '=', self.id)
        ])
        
        return mappings.mapped('timesheet_line_id')
    
    def get_time_since_commit(self):
        """Get human-readable time since commit.
        
        Returns:
            str: Time since commit (e.g., "2 days ago")
        """
        self.ensure_one()
        
        if not self.commit_date:
            return 'Unknown'
        
        now = datetime.now()
        commit_dt = self.commit_date
        
        # Ensure commit_dt is a datetime object
        if hasattr(commit_dt, 'replace'):
            # It's already a datetime object
            pass
        else:
            # Convert from Odoo datetime field
            commit_dt = fields.Datetime.from_string(commit_dt)
        
        delta = now - commit_dt
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @api.model
    def search_commits(self, repository_id, search_term=None, branch=None, 
                      author=None, date_from=None, date_to=None, 
                      commit_type=None, mapped_status=None):
        """Advanced search for commits.
        
        Args:
            repository_id: Repository to search in
            search_term: Search in commit message or hash
            branch: Filter by branch
            author: Filter by author
            date_from: Start date filter
            date_to: End date filter  
            commit_type: Filter by commit type
            mapped_status: 'mapped', 'unmapped', or None for all
            
        Returns:
            recordset: Matching commits
        """
        domain = [('repository_id', '=', repository_id)]
        
        if search_term:
            domain.append('|')
            domain.append(('commit_message', 'ilike', search_term))
            domain.append(('commit_hash', 'ilike', search_term))
        
        if branch:
            domain.append(('branch_name', '=', branch))
        
        if author:
            domain.append('|')
            domain.append(('author_name', 'ilike', author))
            domain.append(('author_email', 'ilike', author))
        
        if date_from:
            domain.append(('commit_date', '>=', date_from))
        
        if date_to:
            domain.append(('commit_date', '<=', date_to))
        
        if commit_type:
            domain.append(('commit_type', '=', commit_type))
        
        if mapped_status == 'mapped':
            domain.append(('is_mapped', '=', True))
        elif mapped_status == 'unmapped':
            domain.append(('is_mapped', '=', False))
        
        return self.search(domain)
    
    @api.model
    def get_commit_statistics(self, repository_id=None, date_from=None, date_to=None):
        """Get commit statistics.
        
        Args:
            repository_id: Optional repository filter
            date_from: Optional start date
            date_to: Optional end date
            
        Returns:
            dict: Statistics data
        """
        domain = []
        
        if repository_id:
            domain.append(('repository_id', '=', repository_id))
        
        if date_from:
            domain.append(('commit_date', '>=', date_from))
        
        if date_to:
            domain.append(('commit_date', '<=', date_to))
        
        commits = self.search(domain)
        
        return {
            'total_commits': len(commits),
            'mapped_commits': len(commits.filtered('is_mapped')),
            'unmapped_commits': len(commits.filtered(lambda c: not c.is_mapped)),
            'unique_authors': len(set(commits.mapped('author_name'))),
            'total_lines_added': sum(commits.mapped('lines_added')),
            'total_lines_deleted': sum(commits.mapped('lines_deleted')),
            'total_files_changed': sum(commits.mapped('files_changed')),
            'commit_types': {
                commit_type: len(commits.filtered(lambda c: c.commit_type == commit_type))
                for commit_type in dict(self._fields['commit_type'].selection).keys()
            }
        }
