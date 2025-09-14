# Data Model: Git Repository Commit to Timesheet Mapping Addon

**Date**: September 13, 2025  
**Version**: 1.0.0  
**Based on**: Odoo 18.0 ORM Standards

## Core Entities

### 1. Git Repository (`git.repository`)

**Purpose**: Stores configured repository connections with authentication details

**Fields**:
- `name` (Char, required): Display name for the repository
- `repository_type` (Selection, required): ['github', 'gitlab'] - Platform type
- `repository_url` (Char, required): Full repository URL (e.g., https://github.com/user/repo)
- `repository_owner` (Char, required): Repository owner/organization name
- `repository_name` (Char, required): Repository name
- `access_token` (Char): Encrypted API access token
- `is_private` (Boolean): Whether repository is private (affects authentication)
- `connection_status` (Selection): ['disconnected', 'connected', 'error'] - Current status
- `last_sync` (Datetime): Last successful synchronization timestamp
- `sync_error_message` (Text): Last error message if connection failed
- `active` (Boolean, default=True): Standard Odoo active field
- `company_id` (Many2one, 'res.company'): Multi-company support
- `user_id` (Many2one, 'res.users'): User who created the connection

**Constraints**:
- Unique constraint on (repository_url, company_id)
- URL validation for proper Git repository format
- Required access_token when is_private=True

**Security**:
- Access token stored encrypted using Odoo's encryption utilities
- Only admin users can create/modify repositories
- Read access restricted by company_id

### 2. Git Commit (`git.commit`)

**Purpose**: Stores individual commit information fetched from repositories

**Fields**:
- `repository_id` (Many2one, 'git.repository', required): Parent repository
- `commit_hash` (Char, required): Full commit SHA hash
- `commit_hash_short` (Char, computed): First 8 characters of commit hash
- `author_name` (Char, required): Commit author name
- `author_email` (Char, required): Commit author email
- `commit_date` (Datetime, required): Commit timestamp (UTC)
- `commit_message` (Text, required): Full commit message
- `commit_message_short` (Char, computed): First line of commit message
- `branch_name` (Char, required): Branch where commit was made
- `files_changed` (Integer): Number of files modified
- `lines_added` (Integer): Lines of code added
- `lines_deleted` (Integer): Lines of code deleted
- `is_mapped` (Boolean, default=False): Whether commit is mapped to timesheet
- `mapped_date` (Datetime): When commit was mapped
- `mapped_by` (Many2one, 'res.users'): User who performed the mapping
- `company_id` (Many2one, 'res.company'): Multi-company support

**Constraints**:
- Unique constraint on (repository_id, commit_hash)
- Author email validation
- Positive values for file/line counts

**Computed Fields**:
- `display_name`: Formatted as "[short_hash] commit_message_short"
- `commit_url`: Full URL to view commit on Git platform

**Methods**:
- `mark_as_mapped()`: Set is_mapped=True and update mapping metadata
- `unmap_commit()`: Reset mapping status (admin only)

### 3. Timesheet Mapping (`timesheet.commit.mapping`)

**Purpose**: Links Git commits to Odoo timesheet entries with mapping metadata

**Fields**:
- `timesheet_line_id` (Many2one, 'account.analytic.line', required): Target timesheet entry
- `commit_id` (Many2one, 'git.commit', required): Source commit
- `mapping_date` (Datetime, default=now): When mapping was created
- `mapped_by` (Many2one, 'res.users', required): User who created mapping
- `mapping_method` (Selection): ['manual', 'bulk', 'auto'] - How mapping was created
- `description` (Text): Optional notes about the mapping
- `active` (Boolean, default=True): Standard Odoo active field
- `company_id` (Many2one, 'res.company'): Multi-company support

**Constraints**:
- Unique constraint on (timesheet_line_id, commit_id) - prevents duplicate mappings
- Validate that commit and timesheet belong to same company

**Related Fields**:
- `project_id` (related='timesheet_line_id.project_id'): Project from timesheet
- `task_id` (related='timesheet_line_id.task_id'): Task from timesheet
- `repository_id` (related='commit_id.repository_id'): Repository from commit

### 4. Extended Timesheet Line (`account.analytic.line`)

**Purpose**: Extends standard Odoo timesheet with commit tracking

**Added Fields**:
- `commit_count` (Integer, computed): Number of mapped commits
- `has_commits` (Boolean, computed): Whether timesheet has mapped commits
- `commit_ids` (One2many, 'timesheet.commit.mapping'): Related commit mappings

**Added Methods**:
- `action_view_commits()`: Open view showing mapped commits
- `unlink_commits()`: Remove all commit mappings (with confirmation)

## Entity Relationships

```
git.repository (1) ────────── (M) git.commit
       │                            │
       │                            │
       └─── (M) timesheet.commit.mapping (M) ───┘
                       │
                       │
                       └── (1) account.analytic.line
                              │
                              └── (1) project.project
                                     │
                                     └── (M) project.task
```

## Database Indexes

**Performance Optimization**:
- `git_commit_repository_date_idx`: (repository_id, commit_date DESC)
- `git_commit_mapped_status_idx`: (is_mapped, company_id)
- `timesheet_mapping_lookup_idx`: (timesheet_line_id, active)
- `git_repository_status_idx`: (connection_status, company_id)

## Data Validation Rules

### Repository Validation
- URL must be valid Git repository format
- Access token required for private repositories
- Repository owner/name extracted from URL
- Connection test before saving

### Commit Validation
- Commit hash must be valid SHA format (40 characters, hexadecimal)
- Author email must be valid email format
- Commit date cannot be in the future
- Lines added/deleted must be non-negative

### Mapping Validation
- Cannot map same commit to multiple timesheets
- Timesheet and commit must belong to same company
- Only active commits can be mapped
- Mapping user must have timesheet write access

## State Transitions

### Repository Connection States
1. **disconnected** → **connected**: Successful authentication test
2. **connected** → **error**: Authentication failure or API error
3. **error** → **connected**: Successful re-authentication
4. **any** → **disconnected**: Manual disconnection by user

### Commit Mapping States
1. **unmapped** (is_mapped=False) → **mapped** (is_mapped=True): User creates mapping
2. **mapped** → **unmapped**: Admin removes mapping (rare operation)

## Security Model

### Access Control Lists (ACL)

**git.repository**:
- Admin: Full CRUD access
- User: Read access to company repositories only

**git.commit**:
- Admin: Full CRUD access
- User: Read access, can update is_mapped status

**timesheet.commit.mapping**:
- Admin: Full CRUD access
- User: Create/read own mappings, cannot delete others' mappings

### Record Rules
- All models filtered by company_id for multi-company support
- Users can only access repositories they have been granted access to
- Timesheet mappings follow existing timesheet security rules

## Migration Strategy

### Initial Installation
1. Create all models and fields
2. Set up security rules and access controls
3. Initialize default data (if any)

### Future Upgrades
- Use standard Odoo migration scripts
- Preserve existing data integrity
- Handle schema changes gracefully
- Provide data migration tools if needed

## Performance Considerations

### Caching Strategy
- Repository connection status cached for 5 minutes
- Commit data cached based on last_sync timestamp
- Heavy queries use database indexes

### Batch Operations
- Bulk commit fetching in batches of 100
- Bulk mapping operations use database transactions
- Background jobs for large repository synchronization

### Memory Management
- Limit commit history to configurable timeframe (default: 6 months)
- Archive old mappings instead of deletion
- Compress commit messages over certain length
