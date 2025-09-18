# -*- coding: utf-8 -*-
{
    'name': 'Git Repository Commit to Timesheet Mapping',
    'version': '1.0.0',
    'category': 'Project',
    'summary': 'Map Git commits to project timesheets with GitHub/GitLab integration',
    'description': """
        Git Repository Commit to Timesheet Mapping Addon
        =================================================
        
        This addon enables automatic tracking of developer time by mapping Git commits 
        to specific project tasks and timesheets. Key features include:
        
        * Connect to GitHub and GitLab repositories (public and private)
        * Fetch commits by repository, branch, and date range
        * Map individual or bulk commits to project timesheets
        * Prevent duplicate mappings with visual indicators
        * User-friendly interface with filtering and search capabilities
        * Role-based access control for repository management
        * Comprehensive audit trail and mapping history
        
        Compatible with Odoo 18.0-20250807 and integrates seamlessly with 
        existing project management and timesheet modules.
    """,
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'project',
        'hr_timesheet',
        'web',
    ],
    'external_dependencies': {
        'python': [
            'PyGithub',
            'python-gitlab', 
            'requests',
            'python-dateutil',
        ],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/assets.xml',
        'views/git_repository_views.xml',
        'views/git_commit_views.xml',
        'views/timesheet_mapping_views.xml',
        'wizard/bulk_mapping_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'git_timesheet_mapper/static/src/js/commit_browser.js',
            'git_timesheet_mapper/static/src/js/bulk_mapper.js',
            'git_timesheet_mapper/static/src/css/styles.css',
            'git_timesheet_mapper/static/src/xml/templates.xml',
        ],
    },
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
}
