# API Contracts: Git Repository Integration

**Date**: September 13, 2025  
**Version**: 1.0.0  
**Protocol**: Odoo JSON-RPC / Web Controllers

## Repository Management Endpoints

### POST /git_timesheet_mapper/repository/create
**Purpose**: Create new repository connection

**Request**:
```json
{
    "name": "string (required)",
    "repository_type": "github|gitlab (required)",
    "repository_url": "string (required, valid Git URL)",
    "access_token": "string (optional for public repos)",
    "is_private": "boolean (default: false)"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "id": "integer",
        "name": "string",
        "repository_type": "string",
        "repository_url": "string",
        "connection_status": "connected|disconnected|error",
        "last_sync": "datetime|null"
    }
}
```

**Response Error (400)**:
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR|AUTH_ERROR|CONNECTION_ERROR",
        "message": "string",
        "details": {}
    }
}
```

### POST /git_timesheet_mapper/repository/test_connection
**Purpose**: Test repository connection without saving

**Request**:
```json
{
    "repository_type": "github|gitlab (required)",
    "repository_url": "string (required)",
    "access_token": "string (optional)"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "connection_status": "connected",
        "repository_info": {
            "name": "string",
            "owner": "string",
            "description": "string",
            "is_private": "boolean",
            "default_branch": "string"
        }
    }
}
```

### GET /git_timesheet_mapper/repository/{id}/branches
**Purpose**: Get available branches for repository

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "branches": [
            {
                "name": "string",
                "commit_hash": "string",
                "commit_date": "datetime"
            }
        ]
    }
}
```

## Commit Management Endpoints

### POST /git_timesheet_mapper/commits/fetch
**Purpose**: Fetch commits from repository branch

**Request**:
```json
{
    "repository_id": "integer (required)",
    "branch_name": "string (required)",
    "date_from": "date (optional)",
    "date_to": "date (optional)",
    "author_filter": "string (optional)",
    "message_filter": "string (optional)"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "total_commits": "integer",
        "new_commits": "integer",
        "commits": [
            {
                "id": "integer",
                "commit_hash": "string",
                "commit_hash_short": "string",
                "author_name": "string",
                "author_email": "string",
                "commit_date": "datetime",
                "commit_message": "string",
                "commit_message_short": "string",
                "branch_name": "string",
                "files_changed": "integer",
                "lines_added": "integer",
                "lines_deleted": "integer",
                "is_mapped": "boolean",
                "commit_url": "string"
            }
        ]
    }
}
```

### GET /git_timesheet_mapper/commits/search
**Purpose**: Search and filter commits

**Query Parameters**:
- `repository_id`: integer (required)
- `branch_name`: string (optional)
- `author`: string (optional)
- `message`: string (optional)
- `date_from`: date (optional)
- `date_to`: date (optional)
- `is_mapped`: boolean (optional)
- `limit`: integer (default: 100)
- `offset`: integer (default: 0)

**Response**: Same as fetch endpoint

## Timesheet Mapping Endpoints

### POST /git_timesheet_mapper/mapping/create
**Purpose**: Create single commit to timesheet mapping

**Request**:
```json
{
    "commit_id": "integer (required)",
    "timesheet_line_id": "integer (required)",
    "description": "string (optional)"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "mapping_id": "integer",
        "commit_id": "integer",
        "timesheet_line_id": "integer",
        "mapping_date": "datetime",
        "mapped_by": "string (user name)"
    }
}
```

### POST /git_timesheet_mapper/mapping/bulk_create
**Purpose**: Create multiple commit mappings at once

**Request**:
```json
{
    "commit_ids": ["integer", "integer", ...],
    "timesheet_line_id": "integer (required)",
    "description": "string (optional)"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "created_mappings": "integer",
        "failed_mappings": [
            {
                "commit_id": "integer",
                "error": "string"
            }
        ],
        "mapping_ids": ["integer", "integer", ...]
    }
}
```

### DELETE /git_timesheet_mapper/mapping/{id}
**Purpose**: Remove commit mapping (admin only)

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "message": "Mapping removed successfully"
    }
}
```

## Bulk Operations Endpoints

### POST /git_timesheet_mapper/bulk/auto_map
**Purpose**: Auto-map commits based on rules

**Request**:
```json
{
    "repository_id": "integer (required)",
    "project_id": "integer (required)",
    "task_id": "integer (optional)",
    "author_email": "string (optional)",
    "date_from": "date (required)",
    "date_to": "date (required)",
    "mapping_rules": {
        "time_per_commit": "float (hours, optional)",
        "match_author_to_user": "boolean (default: true)"
    }
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "processed_commits": "integer",
        "mapped_commits": "integer",
        "skipped_commits": "integer",
        "errors": [
            {
                "commit_id": "integer",
                "error": "string"
            }
        ]
    }
}
```

## Dashboard/Statistics Endpoints

### GET /git_timesheet_mapper/stats/overview
**Purpose**: Get mapping overview statistics

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "total_repositories": "integer",
        "active_repositories": "integer",
        "total_commits": "integer",
        "mapped_commits": "integer",
        "unmapped_commits": "integer",
        "recent_mappings": [
            {
                "mapping_id": "integer",
                "commit_hash_short": "string",
                "project_name": "string",
                "task_name": "string",
                "mapped_date": "datetime",
                "mapped_by": "string"
            }
        ]
    }
}
```

### GET /git_timesheet_mapper/stats/repository/{id}
**Purpose**: Get statistics for specific repository

**Response Success (200)**:
```json
{
    "success": true,
    "data": {
        "repository_name": "string",
        "total_commits": "integer",
        "mapped_commits": "integer",
        "unmapped_commits": "integer",
        "last_sync": "datetime",
        "commit_distribution": {
            "by_author": [
                {
                    "author_name": "string",
                    "commit_count": "integer",
                    "mapped_count": "integer"
                }
            ],
            "by_date": [
                {
                    "date": "date",
                    "commit_count": "integer",
                    "mapped_count": "integer"
                }
            ]
        }
    }
}
```

## Error Codes and Messages

### Authentication Errors
- `AUTH_TOKEN_INVALID`: "Access token is invalid or expired"
- `AUTH_TOKEN_REQUIRED`: "Access token required for private repository"
- `AUTH_INSUFFICIENT_PERMISSIONS`: "Token lacks required repository permissions"

### Repository Errors
- `REPO_NOT_FOUND`: "Repository not found or access denied"
- `REPO_URL_INVALID`: "Invalid repository URL format"
- `REPO_CONNECTION_FAILED`: "Failed to connect to repository"
- `REPO_SYNC_ERROR`: "Error synchronizing repository data"

### Mapping Errors
- `MAPPING_DUPLICATE`: "Commit already mapped to timesheet"
- `MAPPING_COMMIT_NOT_FOUND`: "Commit not found"
- `MAPPING_TIMESHEET_NOT_FOUND`: "Timesheet entry not found"
- `MAPPING_PERMISSION_DENIED`: "Insufficient permissions for mapping"

### Validation Errors
- `VALIDATION_REQUIRED_FIELD`: "Required field missing: {field_name}"
- `VALIDATION_INVALID_FORMAT`: "Invalid format for field: {field_name}"
- `VALIDATION_VALUE_TOO_LONG`: "Value too long for field: {field_name}"

## Rate Limiting

**Repository Operations**:
- Connection tests: 10 requests per minute per user
- Branch listing: 20 requests per minute per user
- Commit fetching: 5 requests per minute per repository

**Mapping Operations**:
- Single mapping: 100 requests per minute per user
- Bulk mapping: 10 requests per minute per user

**Error Response for Rate Limiting (429)**:
```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Try again in {seconds} seconds",
        "retry_after": "integer (seconds)"
    }
}
```

## Authentication

All endpoints require:
- Valid Odoo session
- Appropriate user permissions
- CSRF token for POST/PUT/DELETE operations

**Headers**:
```
Content-Type: application/json
X-CSRFToken: {csrf_token}
Cookie: session_id={session_id}
```
