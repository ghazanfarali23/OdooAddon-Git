# Quickstart Guide: Git Repository Commit to Timesheet Mapping Addon

**Version**: 1.0.0  
**Odoo Version**: 18.0-20250807  
**Date**: September 13, 2025

## Prerequisites

### System Requirements
- Odoo 18.0-20250807 installation
- Python 3.10 or higher
- PostgreSQL database
- Internet connectivity for Git API access

### Required Python Packages
```bash
pip install PyGithub==1.59.0
pip install python-gitlab==3.15.0
pip install requests==2.31.0
pip install python-dateutil==2.8.0
```

### Git Repository Access
- GitHub Personal Access Token or GitHub App credentials
- GitLab Personal Access Token or OAuth2 credentials
- Repository read access for target repositories

## Installation Steps

### 1. Install the Addon

**Download and Install**:
```bash
# Clone or copy the addon to your Odoo addons directory
cp -r git_timesheet_mapper /path/to/odoo/addons/

# Update Odoo addons list
odoo-bin -d your_database -u base --stop-after-init

# Install the addon
odoo-bin -d your_database -i git_timesheet_mapper --stop-after-init
```

**Via Odoo Interface**:
1. Go to Apps menu
2. Search for "Git Timesheet Mapper"
3. Click "Install"

### 2. Configure User Permissions

**Admin Setup**:
1. Go to Settings → Users & Companies → Users
2. Edit user accounts
3. Add "Git Repository Manager" group for repository access
4. Add "Timesheet Mapping User" group for mapping operations

### 3. Set Up Your First Repository

**GitHub Repository**:
1. Navigate to Project → Configuration → Git Repositories
2. Click "Create"
3. Fill in repository details:
   - **Name**: "My Project Repository"
   - **Type**: "GitHub"
   - **URL**: "https://github.com/username/repository"
   - **Access Token**: Your GitHub Personal Access Token
   - **Private**: Check if repository is private
4. Click "Test Connection" to verify
5. Click "Save"

**GitLab Repository**:
1. Navigate to Project → Configuration → Git Repositories
2. Click "Create"
3. Fill in repository details:
   - **Name**: "My GitLab Project"
   - **Type**: "GitLab"
   - **URL**: "https://gitlab.com/username/repository"
   - **Access Token**: Your GitLab Personal Access Token
   - **Private**: Check if repository is private
4. Click "Test Connection" to verify
5. Click "Save"

## Basic Usage Workflow

### Step 1: Fetch Commits

1. Go to Project → Git Integration → Repositories
2. Select your repository
3. Click "Fetch Commits"
4. Choose branch (default: main/master)
5. Set date range (optional)
6. Click "Fetch" - commits will be imported

### Step 2: View and Filter Commits

1. Go to Project → Git Integration → Commits
2. Use filters to find relevant commits:
   - Filter by author
   - Filter by date range
   - Search in commit messages
   - Filter by mapping status

### Step 3: Create Project and Timesheet Entries

1. Go to Project → Projects
2. Create or select a project
3. Create tasks within the project
4. Go to Timesheets → All Timesheets
5. Create timesheet entries for your tasks

### Step 4: Map Commits to Timesheets

**Single Commit Mapping**:
1. Go to Project → Git Integration → Commits
2. Find the commit you want to map
3. Click "Map to Timesheet"
4. Select the timesheet entry
5. Add optional description
6. Click "Create Mapping"

**Bulk Commit Mapping**:
1. Go to Project → Git Integration → Commits
2. Select multiple commits using checkboxes
3. Click "Bulk Map"
4. Select target timesheet entry
5. Click "Map Selected Commits"

## Advanced Features

### Auto-Mapping by Author

1. Go to Project → Git Integration → Bulk Operations
2. Select "Auto Map by Author"
3. Choose repository and date range
4. Map authors to Odoo users
5. Set default time per commit
6. Click "Process"

### Dashboard and Reports

1. Go to Project → Git Integration → Dashboard
2. View mapping statistics:
   - Total commits vs mapped commits
   - Repository activity
   - Recent mappings
   - Author contribution charts

### Repository Synchronization

**Manual Sync**:
1. Go to repository record
2. Click "Sync Now"
3. System fetches latest commits

**Automatic Sync** (if configured):
- Runs daily via scheduled action
- Fetches commits from last 7 days
- Sends notifications for sync errors

## Troubleshooting

### Common Issues

**"Connection Failed" Error**:
- Check internet connectivity
- Verify repository URL is correct
- Ensure access token has proper permissions
- For private repos, verify token is provided

**"Authentication Failed" Error**:
- Access token may be expired or revoked
- Check token permissions in Git platform
- Generate new token if needed

**"Repository Not Found" Error**:
- Verify repository URL spelling
- Check if repository was renamed/moved
- Ensure you have access to the repository

**Commits Not Appearing**:
- Check date range filters
- Verify you're looking at correct branch
- Ensure commits exist in the selected timeframe

**Mapping Errors**:
- Verify timesheet entry exists and is accessible
- Check if commit is already mapped elsewhere
- Ensure you have write permissions on timesheet

### Error Logs

**View System Logs**:
1. Go to Settings → Technical → Logging
2. Filter by "git_timesheet_mapper"
3. Review error messages and stack traces

**Enable Debug Mode**:
1. Add `?debug=1` to URL
2. View detailed error information
3. Access developer tools

### Performance Optimization

**Large Repositories**:
- Limit date ranges when fetching commits
- Use author filters to reduce commit volume
- Consider archiving old commits periodically

**Slow API Responses**:
- Check Git platform status pages
- Verify network connectivity
- Consider caching for frequently accessed data

## Security Best Practices

### Token Management

**GitHub Personal Access Tokens**:
- Use tokens with minimal required permissions
- Set expiration dates on tokens
- Rotate tokens regularly
- Store tokens securely in Odoo encrypted fields

**GitLab Personal Access Tokens**:
- Use "read_repository" scope only
- Set expiration dates
- Monitor token usage in GitLab audit logs

### Access Control

**Repository Access**:
- Limit repository management to administrators
- Use record rules to restrict repository visibility
- Audit repository access regularly

**Mapping Permissions**:
- Users can only map to their own timesheets
- Managers can map to team member timesheets
- Maintain audit trail of all mapping operations

## Integration Examples

### Webhook Integration

**GitHub Webhooks** (Advanced):
```python
# Custom controller for webhook events
@http.route('/git_webhook/github', type='json', auth='none', csrf=False)
def github_webhook(self, **kwargs):
    # Automatically sync commits when pushed
    # Trigger mapping workflows
    # Send notifications
```

**GitLab Webhooks** (Advanced):
```python
# Custom controller for GitLab events
@http.route('/git_webhook/gitlab', type='json', auth='none', csrf=False)
def gitlab_webhook(self, **kwargs):
    # Handle push events
    # Update commit status
    # Trigger automated workflows
```

### Custom Automation

**Scheduled Actions**:
- Daily commit synchronization
- Weekly mapping reports
- Monthly cleanup of old data

**Email Notifications**:
- Notify on mapping completion
- Alert on synchronization failures
- Weekly activity summaries

## Support and Documentation

### Additional Resources
- [Odoo Documentation](https://www.odoo.com/documentation/18.0/)
- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitLab API Documentation](https://docs.gitlab.com/ee/api/)

### Getting Help
1. Check error logs first
2. Review this quickstart guide
3. Contact system administrator
4. Consult Odoo community forums

### Contributing
- Report bugs through Odoo interface
- Suggest features via feedback system
- Contribute to documentation improvements

---

**Next Steps**: Once you've completed the quickstart, explore the bulk mapping features and dashboard reports to maximize your productivity with the Git Timesheet Mapper addon.
