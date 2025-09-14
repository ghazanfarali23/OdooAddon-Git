/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Bulk Mapping Component
 * 
 * Interactive component for bulk mapping Git commits to timesheet entries.
 * Provides drag-and-drop functionality, intelligent matching suggestions,
 * and progress tracking for bulk operations.
 */
export class BulkMappingComponent extends Component {
    static template = "git_timesheet_mapper.BulkMapper";
    static props = {
        commitIds: { type: Array, optional: true },
        projectId: { type: Number, optional: true },
        onMappingComplete: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
    };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            // Step management
            currentStep: 1,
            totalSteps: 4,
            canProceed: false,
            
            // Commit data
            commits: [],
            selectedCommits: new Set(this.props.commitIds || []),
            commitFilters: {
                repository: null,
                branch: null,
                author: null,
                dateFrom: this._getDefaultDateFrom(),
                dateTo: this._getDefaultDateTo(),
                commitType: null,
                onlyUnmapped: true,
            },
            
            // Timesheet data
            timesheets: [],
            selectedTimesheets: new Set(),
            timesheetFilters: {
                project: this.props.projectId || null,
                task: null,
                employee: null,
                dateFrom: this._getDefaultDateFrom(),
                dateTo: this._getDefaultDateTo(),
            },
            
            // Mapping configuration
            mappingMethod: 'bulk',
            mappingDescription: '',
            autoVerify: false,
            mappingStrategy: 'intelligent', // 'intelligent', 'sequential', 'manual'
            
            // Preview and suggestions
            mappingSuggestions: [],
            previewMappings: [],
            confidenceThreshold: 70,
            
            // Processing
            isProcessing: false,
            processedCount: 0,
            totalToProcess: 0,
            processingStatus: '',
            errors: [],
            
            // Results
            createdMappings: 0,
            failedMappings: 0,
            completionTime: null,
            
            // UI state
            loading: false,
            draggedCommit: null,
            dropTarget: null,
            showAdvancedOptions: false,
        });

        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
    }

    async onWillStart() {
        if (this.props.commitIds && this.props.commitIds.length > 0) {
            await this.loadCommitsFromIds();
            this.state.currentStep = 2; // Skip to timesheet selection
        } else {
            await this.loadRepositories();
        }
    }

    onMounted() {
        this.setupDragAndDrop();
        this.updateCanProceed();
    }

    // Step Navigation
    async nextStep() {
        if (!this.state.canProceed) return;

        switch (this.state.currentStep) {
            case 1:
                await this.proceedToTimesheetSelection();
                break;
            case 2:
                await this.proceedToMappingPreview();
                break;
            case 3:
                await this.proceedToProcessing();
                break;
            case 4:
                this.finish();
                break;
        }
    }

    async prevStep() {
        if (this.state.currentStep > 1) {
            this.state.currentStep--;
            this.updateCanProceed();
        }
    }

    updateCanProceed() {
        switch (this.state.currentStep) {
            case 1:
                this.state.canProceed = this.state.selectedCommits.size > 0;
                break;
            case 2:
                this.state.canProceed = this.state.selectedTimesheets.size > 0;
                break;
            case 3:
                this.state.canProceed = this.state.previewMappings.length > 0;
                break;
            case 4:
                this.state.canProceed = false;
                break;
        }
    }

    // Step 1: Commit Selection
    async loadRepositories() {
        try {
            this.state.loading = true;
            const repositories = await this.orm.searchRead(
                "git.repository",
                [["connection_status", "=", "connected"]],
                ["id", "name", "repository_type"]
            );
            this.state.repositories = repositories;
        } finally {
            this.state.loading = false;
        }
    }

    async loadCommitsFromIds() {
        try {
            this.state.loading = true;
            const commits = await this.orm.searchRead(
                "git.commit",
                [["id", "in", this.props.commitIds]],
                ["id", "commit_hash", "short_hash", "commit_message_short", "author_name", 
                 "commit_date", "commit_type", "is_mapped", "repository_id", "branch_name"]
            );
            this.state.commits = commits;
        } finally {
            this.state.loading = false;
        }
    }

    async loadCommits() {
        try {
            this.state.loading = true;
            const domain = this._buildCommitDomain();
            const commits = await this.orm.searchRead(
                "git.commit",
                domain,
                ["id", "commit_hash", "short_hash", "commit_message_short", "author_name", 
                 "commit_date", "commit_type", "is_mapped", "repository_id", "branch_name"],
                { limit: 100, order: "commit_date desc" }
            );
            this.state.commits = commits;
        } finally {
            this.state.loading = false;
            this.updateCanProceed();
        }
    }

    _buildCommitDomain() {
        const domain = [];
        
        if (this.state.commitFilters.repository) {
            domain.push(["repository_id", "=", this.state.commitFilters.repository]);
        }
        if (this.state.commitFilters.branch) {
            domain.push(["branch_name", "=", this.state.commitFilters.branch]);
        }
        if (this.state.commitFilters.author) {
            domain.push("|", ["author_name", "ilike", this.state.commitFilters.author], 
                        ["author_email", "ilike", this.state.commitFilters.author]);
        }
        if (this.state.commitFilters.dateFrom) {
            domain.push(["commit_date", ">=", this.state.commitFilters.dateFrom]);
        }
        if (this.state.commitFilters.dateTo) {
            domain.push(["commit_date", "<=", this.state.commitFilters.dateTo]);
        }
        if (this.state.commitFilters.commitType) {
            domain.push(["commit_type", "=", this.state.commitFilters.commitType]);
        }
        if (this.state.commitFilters.onlyUnmapped) {
            domain.push(["is_mapped", "=", false]);
        }
        
        return domain;
    }

    toggleCommitSelection(commitId) {
        if (this.state.selectedCommits.has(commitId)) {
            this.state.selectedCommits.delete(commitId);
        } else {
            this.state.selectedCommits.add(commitId);
        }
        this.updateCanProceed();
    }

    selectAllCommits() {
        this.state.commits.forEach(commit => {
            this.state.selectedCommits.add(commit.id);
        });
        this.updateCanProceed();
    }

    deselectAllCommits() {
        this.state.selectedCommits.clear();
        this.updateCanProceed();
    }

    async proceedToTimesheetSelection() {
        this.state.currentStep = 2;
        await this.loadTimesheets();
        this.updateCanProceed();
    }

    // Step 2: Timesheet Selection
    async loadTimesheets() {
        try {
            this.state.loading = true;
            const domain = this._buildTimesheetDomain();
            const timesheets = await this.orm.searchRead(
                "account.analytic.line",
                domain,
                ["id", "name", "project_id", "task_id", "employee_id", "date", "unit_amount"],
                { limit: 100, order: "date desc" }
            );
            this.state.timesheets = timesheets;
        } finally {
            this.state.loading = false;
            this.updateCanProceed();
        }
    }

    _buildTimesheetDomain() {
        const domain = [["project_id", "!=", false]];
        
        if (this.state.timesheetFilters.project) {
            domain.push(["project_id", "=", this.state.timesheetFilters.project]);
        }
        if (this.state.timesheetFilters.task) {
            domain.push(["task_id", "=", this.state.timesheetFilters.task]);
        }
        if (this.state.timesheetFilters.employee) {
            domain.push(["employee_id", "=", this.state.timesheetFilters.employee]);
        }
        if (this.state.timesheetFilters.dateFrom) {
            domain.push(["date", ">=", this.state.timesheetFilters.dateFrom]);
        }
        if (this.state.timesheetFilters.dateTo) {
            domain.push(["date", "<=", this.state.timesheetFilters.dateTo]);
        }
        
        return domain;
    }

    toggleTimesheetSelection(timesheetId) {
        if (this.state.selectedTimesheets.has(timesheetId)) {
            this.state.selectedTimesheets.delete(timesheetId);
        } else {
            this.state.selectedTimesheets.add(timesheetId);
        }
        this.updateCanProceed();
    }

    selectAllTimesheets() {
        this.state.timesheets.forEach(timesheet => {
            this.state.selectedTimesheets.add(timesheet.id);
        });
        this.updateCanProceed();
    }

    deselectAllTimesheets() {
        this.state.selectedTimesheets.clear();
        this.updateCanProceed();
    }

    async proceedToMappingPreview() {
        this.state.currentStep = 3;
        await this.generateMappingSuggestions();
        this.updateCanProceed();
    }

    // Step 3: Mapping Preview
    async generateMappingSuggestions() {
        try {
            this.state.loading = true;
            
            if (this.state.mappingStrategy === 'intelligent') {
                await this.generateIntelligentMappings();
            } else if (this.state.mappingStrategy === 'sequential') {
                this.generateSequentialMappings();
            } else {
                this.generateManualMappings();
            }
        } finally {
            this.state.loading = false;
        }
    }

    async generateIntelligentMappings() {
        try {
            const result = await this.rpc("/git_timesheet_mapper/mapping/suggestions", {
                commit_ids: Array.from(this.state.selectedCommits),
                timesheet_line_ids: Array.from(this.state.selectedTimesheets),
                limit: 50
            });

            if (result.success) {
                this.state.mappingSuggestions = result.suggestions || [];
                this.state.previewMappings = this.state.mappingSuggestions.filter(
                    s => s.confidence_score >= this.state.confidenceThreshold
                );
            } else {
                this.notification.add(result.error || _t("Error generating suggestions"), { type: "danger" });
                this.generateSequentialMappings();
            }
        } catch (error) {
            console.error("Error generating intelligent mappings:", error);
            this.generateSequentialMappings();
        }
    }

    generateSequentialMappings() {
        this.state.previewMappings = [];
        const commits = Array.from(this.state.selectedCommits);
        const timesheets = Array.from(this.state.selectedTimesheets);
        
        commits.forEach((commitId, index) => {
            const timesheetIndex = index % timesheets.length;
            const timesheetId = timesheets[timesheetIndex];
            
            this.state.previewMappings.push({
                commit_id: commitId,
                timesheet_id: timesheetId,
                confidence_score: 50,
                mapping_method: this.state.mappingMethod,
                suggested: false,
            });
        });
    }

    generateManualMappings() {
        this.state.previewMappings = [];
        // Manual mappings will be created via drag and drop
    }

    removeMappingPreview(index) {
        this.state.previewMappings.splice(index, 1);
        this.updateCanProceed();
    }

    addManualMapping(commitId, timesheetId) {
        // Check if mapping already exists
        const exists = this.state.previewMappings.some(
            m => m.commit_id === commitId && m.timesheet_id === timesheetId
        );
        
        if (!exists) {
            this.state.previewMappings.push({
                commit_id: commitId,
                timesheet_id: timesheetId,
                confidence_score: 100, // Manual mappings have 100% confidence
                mapping_method: this.state.mappingMethod,
                suggested: false,
            });
        }
        this.updateCanProceed();
    }

    async proceedToProcessing() {
        this.state.currentStep = 4;
        this.state.totalToProcess = this.state.previewMappings.length;
        await this.processMappings();
    }

    // Step 4: Processing
    async processMappings() {
        this.state.isProcessing = true;
        this.state.processedCount = 0;
        this.state.createdMappings = 0;
        this.state.failedMappings = 0;
        this.state.errors = [];
        
        const startTime = Date.now();

        try {
            for (let i = 0; i < this.state.previewMappings.length; i++) {
                const mapping = this.state.previewMappings[i];
                this.state.processingStatus = _t("Processing mapping %s of %s", i + 1, this.state.totalToProcess);
                
                try {
                    const result = await this.rpc("/git_timesheet_mapper/mapping/create", {
                        commit_id: mapping.commit_id,
                        timesheet_line_id: mapping.timesheet_id,
                        description: this.state.mappingDescription,
                        mapping_method: this.state.mappingMethod,
                        auto_verify: this.state.autoVerify,
                    });

                    if (result.success) {
                        this.state.createdMappings++;
                    } else {
                        this.state.failedMappings++;
                        this.state.errors.push(`Mapping ${i + 1}: ${result.error}`);
                    }
                } catch (error) {
                    this.state.failedMappings++;
                    this.state.errors.push(`Mapping ${i + 1}: ${error.message}`);
                }
                
                this.state.processedCount++;
                
                // Small delay to show progress
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } finally {
            this.state.isProcessing = false;
            this.state.completionTime = Date.now() - startTime;
            this.state.processingStatus = _t("Processing complete");
            
            // Show completion notification
            if (this.state.createdMappings > 0) {
                this.notification.add(
                    _t("Created %s mappings successfully", this.state.createdMappings),
                    { type: "success" }
                );
            }
            
            if (this.state.failedMappings > 0) {
                this.notification.add(
                    _t("%s mappings failed", this.state.failedMappings),
                    { type: "warning" }
                );
            }
        }
    }

    // Drag and Drop functionality
    setupDragAndDrop() {
        // Will be implemented in the template with drag/drop event handlers
    }

    onCommitDragStart(ev, commitId) {
        this.state.draggedCommit = commitId;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", commitId);
    }

    onTimesheetDragOver(ev, timesheetId) {
        if (this.state.draggedCommit) {
            ev.preventDefault();
            this.state.dropTarget = timesheetId;
        }
    }

    onTimesheetDrop(ev, timesheetId) {
        ev.preventDefault();
        if (this.state.draggedCommit) {
            this.addManualMapping(this.state.draggedCommit, timesheetId);
            this.state.draggedCommit = null;
            this.state.dropTarget = null;
        }
    }

    onDragEnd() {
        this.state.draggedCommit = null;
        this.state.dropTarget = null;
    }

    // Utility methods
    _getDefaultDateFrom() {
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    _getDefaultDateTo() {
        return new Date().toISOString().split('T')[0];
    }

    getCommit(commitId) {
        return this.state.commits.find(c => c.id === commitId);
    }

    getTimesheet(timesheetId) {
        return this.state.timesheets.find(t => t.id === timesheetId);
    }

    getProgressPercentage() {
        if (this.state.totalToProcess === 0) return 0;
        return Math.round((this.state.processedCount / this.state.totalToProcess) * 100);
    }

    getConfidenceClass(score) {
        if (score >= 80) return 'text-success';
        if (score >= 60) return 'text-warning';
        return 'text-danger';
    }

    formatDuration(ms) {
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        return `${minutes}m ${seconds % 60}s`;
    }

    // Actions
    finish() {
        if (this.props.onMappingComplete) {
            this.props.onMappingComplete({
                created: this.state.createdMappings,
                failed: this.state.failedMappings,
                duration: this.state.completionTime,
                errors: this.state.errors,
            });
        }
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
    }
}

// Register the component
registry.category("public_components").add("BulkMappingComponent", BulkMappingComponent);
