/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Git Commit Browser Component
 * 
 * Interactive component for browsing Git commits with filtering, search,
 * and mapping capabilities. Integrates with the Git Timesheet Mapper
 * backend API to provide real-time commit data and mapping operations.
 */
export class GitCommitBrowser extends Component {
    static template = "git_timesheet_mapper.CommitBrowser";
    static props = {
        repositoryId: { type: Number, optional: true },
        showMappedCommits: { type: Boolean, optional: true },
        enableBulkActions: { type: Boolean, optional: true },
        onCommitSelected: { type: Function, optional: true },
        onMappingCreated: { type: Function, optional: true },
    };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        this.state = useState({
            // Data state
            commits: [],
            repositories: [],
            branches: [],
            selectedCommits: new Set(),
            
            // UI state
            loading: false,
            searchTerm: "",
            currentPage: 1,
            totalPages: 1,
            totalCommits: 0,
            
            // Filter state
            selectedRepository: this.props.repositoryId || null,
            selectedBranch: null,
            selectedAuthor: null,
            selectedCommitType: null,
            mappingStatus: this.props.showMappedCommits ? 'all' : 'unmapped',
            dateFrom: this._getDefaultDateFrom(),
            dateTo: this._getDefaultDateTo(),
            
            // View state
            viewMode: 'list', // 'list', 'grid', 'timeline'
            sortBy: 'commit_date',
            sortOrder: 'desc',
            pageSize: 20,
            
            // Bulk actions
            bulkActionMode: false,
            selectedCommitCount: 0,
        });

        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
    }

    async onWillStart() {
        await this.loadRepositories();
        if (this.state.selectedRepository) {
            await this.loadBranches();
            await this.loadCommits();
        }
    }

    onMounted() {
        this.setupKeyboardShortcuts();
        this.setupAutoRefresh();
    }

    // Data Loading Methods
    async loadRepositories() {
        try {
            this.state.loading = true;
            const repositories = await this.orm.searchRead(
                "git.repository",
                [["connection_status", "=", "connected"]],
                ["id", "name", "repository_type", "owner", "repo_name"]
            );
            this.state.repositories = repositories;
        } catch (error) {
            this.notification.add(_t("Error loading repositories"), { type: "danger" });
            console.error("Error loading repositories:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async loadBranches() {
        if (!this.state.selectedRepository) {
            this.state.branches = [];
            return;
        }

        try {
            const result = await this.rpc(
                `/git_timesheet_mapper/repository/${this.state.selectedRepository}/branches`,
                {}
            );
            
            if (result.success) {
                this.state.branches = result.branches || [];
            } else {
                this.notification.add(result.error || _t("Error loading branches"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(_t("Error loading branches"), { type: "danger" });
            console.error("Error loading branches:", error);
        }
    }

    async loadCommits(page = 1) {
        try {
            this.state.loading = true;
            this.state.currentPage = page;

            const searchParams = this._buildSearchParams();
            const result = await this.rpc("/git_timesheet_mapper/commits/search", searchParams);

            if (result.success) {
                this.state.commits = result.commits || [];
                this.state.totalCommits = result.pagination.total_count;
                this.state.totalPages = Math.ceil(result.pagination.total_count / this.state.pageSize);
                
                // Update selected commits state
                this._updateSelectedCommitsState();
            } else {
                this.notification.add(result.error || _t("Error loading commits"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(_t("Error loading commits"), { type: "danger" });
            console.error("Error loading commits:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async refreshCommits() {
        if (!this.state.selectedRepository) {
            this.notification.add(_t("Please select a repository first"), { type: "warning" });
            return;
        }

        try {
            this.state.loading = true;
            const result = await this.rpc("/git_timesheet_mapper/commits/fetch", {
                repository_id: this.state.selectedRepository,
                branch: this.state.selectedBranch,
            });

            if (result.success) {
                this.notification.add(_t("Commits synced successfully"), { type: "success" });
                await this.loadCommits();
            } else {
                this.notification.add(result.error || _t("Error syncing commits"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(_t("Error syncing commits"), { type: "danger" });
            console.error("Error syncing commits:", error);
        } finally {
            this.state.loading = false;
        }
    }

    // Search and Filter Methods
    _buildSearchParams() {
        const params = {
            repository_id: this.state.selectedRepository,
            limit: this.state.pageSize,
            offset: (this.state.currentPage - 1) * this.state.pageSize,
        };

        if (this.state.searchTerm) {
            params.search_term = this.state.searchTerm;
        }
        if (this.state.selectedBranch) {
            params.branch = this.state.selectedBranch;
        }
        if (this.state.selectedAuthor) {
            params.author = this.state.selectedAuthor;
        }
        if (this.state.selectedCommitType) {
            params.commit_type = this.state.selectedCommitType;
        }
        if (this.state.mappingStatus !== 'all') {
            params.mapped_status = this.state.mappingStatus;
        }
        if (this.state.dateFrom) {
            params.date_from = this.state.dateFrom;
        }
        if (this.state.dateTo) {
            params.date_to = this.state.dateTo;
        }

        return params;
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        this._debounceSearch();
    }

    _debounceSearch() {
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => {
            this.loadCommits(1);
        }, 300);
    }

    onFilterChange() {
        this.loadCommits(1);
    }

    onRepositoryChange(ev) {
        this.state.selectedRepository = parseInt(ev.target.value) || null;
        this.state.selectedBranch = null;
        this.state.branches = [];
        this.state.commits = [];
        this.state.selectedCommits.clear();
        
        if (this.state.selectedRepository) {
            this.loadBranches().then(() => this.loadCommits(1));
        }
    }

    onBranchChange(ev) {
        this.state.selectedBranch = ev.target.value || null;
        this.loadCommits(1);
    }

    clearFilters() {
        this.state.searchTerm = "";
        this.state.selectedBranch = null;
        this.state.selectedAuthor = null;
        this.state.selectedCommitType = null;
        this.state.mappingStatus = this.props.showMappedCommits ? 'all' : 'unmapped';
        this.state.dateFrom = this._getDefaultDateFrom();
        this.state.dateTo = this._getDefaultDateTo();
        this.loadCommits(1);
    }

    // Commit Selection Methods
    onCommitToggle(commitId, ev) {
        ev.stopPropagation();
        
        if (this.state.selectedCommits.has(commitId)) {
            this.state.selectedCommits.delete(commitId);
        } else {
            this.state.selectedCommits.add(commitId);
        }
        
        this.state.selectedCommitCount = this.state.selectedCommits.size;
        
        if (this.props.onCommitSelected) {
            this.props.onCommitSelected(Array.from(this.state.selectedCommits));
        }
    }

    selectAllCommits() {
        this.state.commits.forEach(commit => {
            if (!commit.is_mapped || this.props.showMappedCommits) {
                this.state.selectedCommits.add(commit.id);
            }
        });
        this.state.selectedCommitCount = this.state.selectedCommits.size;
    }

    deselectAllCommits() {
        this.state.selectedCommits.clear();
        this.state.selectedCommitCount = 0;
    }

    toggleBulkMode() {
        this.state.bulkActionMode = !this.state.bulkActionMode;
        if (!this.state.bulkActionMode) {
            this.deselectAllCommits();
        }
    }

    // Mapping Actions
    async createMapping(commitId) {
        try {
            const commit = this.state.commits.find(c => c.id === commitId);
            if (!commit) return;

            // Open mapping dialog/wizard
            this.dialog.add("git_timesheet_mapper.MappingDialog", {
                commitId: commitId,
                onMappingCreated: (mappingData) => {
                    this.notification.add(_t("Mapping created successfully"), { type: "success" });
                    this._updateCommitMappingStatus(commitId, true);
                    
                    if (this.props.onMappingCreated) {
                        this.props.onMappingCreated(mappingData);
                    }
                }
            });
        } catch (error) {
            this.notification.add(_t("Error creating mapping"), { type: "danger" });
            console.error("Error creating mapping:", error);
        }
    }

    async createBulkMapping() {
        if (this.state.selectedCommits.size === 0) {
            this.notification.add(_t("Please select commits first"), { type: "warning" });
            return;
        }

        try {
            // Open bulk mapping wizard with selected commits
            const action = await this.orm.call(
                "bulk.mapping.wizard",
                "create",
                [{
                    selected_commit_ids: [[6, 0, Array.from(this.state.selectedCommits)]],
                    state: 'select_timesheet'
                }]
            );

            this.dialog.add("ir.actions.act_window", {
                res_model: "bulk.mapping.wizard",
                res_id: action,
                view_mode: "form",
                target: "new",
                context: { default_state: 'select_timesheet' }
            });
        } catch (error) {
            this.notification.add(_t("Error opening bulk mapping wizard"), { type: "danger" });
            console.error("Error opening bulk mapping wizard:", error);
        }
    }

    // View Control Methods
    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    setSortBy(field) {
        if (this.state.sortBy === field) {
            this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortBy = field;
            this.state.sortOrder = 'desc';
        }
        this.loadCommits(1);
    }

    // Pagination Methods
    goToPage(page) {
        if (page >= 1 && page <= this.state.totalPages) {
            this.loadCommits(page);
        }
    }

    nextPage() {
        this.goToPage(this.state.currentPage + 1);
    }

    prevPage() {
        this.goToPage(this.state.currentPage - 1);
    }

    // Utility Methods
    _getDefaultDateFrom() {
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    _getDefaultDateTo() {
        return new Date().toISOString().split('T')[0];
    }

    _updateSelectedCommitsState() {
        // Remove selected commits that are no longer in current page
        const currentCommitIds = new Set(this.state.commits.map(c => c.id));
        for (const commitId of this.state.selectedCommits) {
            if (!currentCommitIds.has(commitId)) {
                this.state.selectedCommits.delete(commitId);
            }
        }
        this.state.selectedCommitCount = this.state.selectedCommits.size;
    }

    _updateCommitMappingStatus(commitId, isMapped) {
        const commit = this.state.commits.find(c => c.id === commitId);
        if (commit) {
            commit.is_mapped = isMapped;
            commit.mapping_count = isMapped ? (commit.mapping_count || 0) + 1 : Math.max(0, (commit.mapping_count || 1) - 1);
        }
    }

    setupKeyboardShortcuts() {
        // Ctrl+A: Select all
        // Ctrl+R: Refresh
        // Escape: Clear selection
        document.addEventListener('keydown', (ev) => {
            if (ev.ctrlKey && ev.key === 'a' && this.state.bulkActionMode) {
                ev.preventDefault();
                this.selectAllCommits();
            } else if (ev.ctrlKey && ev.key === 'r') {
                ev.preventDefault();
                this.refreshCommits();
            } else if (ev.key === 'Escape') {
                this.deselectAllCommits();
            }
        });
    }

    setupAutoRefresh() {
        // Auto-refresh every 5 minutes if enabled
        if (this.props.autoRefresh) {
            this._refreshInterval = setInterval(() => {
                if (this.state.selectedRepository && !this.state.loading) {
                    this.loadCommits(this.state.currentPage);
                }
            }, 300000); // 5 minutes
        }
    }

    willUnmount() {
        if (this._refreshInterval) {
            clearInterval(this._refreshInterval);
        }
        if (this._searchTimeout) {
            clearTimeout(this._searchTimeout);
        }
    }

    // Template Helper Methods
    getCommitTypeClass(commitType) {
        const typeClasses = {
            'feature': 'badge-info',
            'bugfix': 'badge-warning',
            'refactor': 'badge-secondary',
            'docs': 'badge-primary',
            'test': 'badge-success',
            'chore': 'badge-dark',
            'other': 'badge-light'
        };
        return typeClasses[commitType] || 'badge-light';
    }

    getMappingStatusClass(isMapped) {
        return isMapped ? 'text-success' : 'text-muted';
    }

    getMappingStatusIcon(isMapped) {
        return isMapped ? 'fa-check-circle' : 'fa-circle-o';
    }

    formatCommitDate(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toLocaleString();
    }

    formatTimeSince(dateString) {
        if (!dateString) return '';
        const now = new Date();
        const commitDate = new Date(dateString);
        const diffMs = now - commitDate;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor(diffMs / (1000 * 60));

        if (diffDays > 0) return `${diffDays}d ago`;
        if (diffHours > 0) return `${diffHours}h ago`;
        if (diffMinutes > 0) return `${diffMinutes}m ago`;
        return 'Just now';
    }

    truncateMessage(message, length = 60) {
        if (!message || message.length <= length) return message;
        return message.substring(0, length) + '...';
    }
}

// Register the component
registry.category("public_components").add("GitCommitBrowser", GitCommitBrowser);
