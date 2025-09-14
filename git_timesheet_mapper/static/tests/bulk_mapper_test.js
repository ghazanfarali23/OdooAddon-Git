/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BulkMappingComponent } from "@git_timesheet_mapper/js/bulk_mapper";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("Git Timesheet Mapper", {}, function () {
    QUnit.module("BulkMappingComponent", {}, function () {
        
        QUnit.test("Component initialization", async function (assert) {
            assert.expect(2);
            
            const component = new BulkMappingComponent();
            assert.ok(component, "Component should be created");
            assert.equal(component.constructor.name, "BulkMappingComponent", "Component should be BulkMappingComponent");
        });

        QUnit.test("State initialization", async function (assert) {
            assert.expect(6);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {
                    commitIds: [1, 2, 3],
                    projectId: 1,
                },
            });
            
            await component.setup();
            
            assert.ok(component.state, "State should be initialized");
            assert.equal(component.state.currentStep, 1, "Initial step should be 1");
            assert.equal(component.state.totalSteps, 4, "Should have 4 total steps");
            assert.ok(component.state.selectedCommits instanceof Set, "Selected commits should be a Set");
            assert.ok(component.state.selectedTimesheets instanceof Set, "Selected timesheets should be a Set");
            assert.ok(Array.isArray(component.state.previewMappings), "Preview mappings should be an array");
        });

        QUnit.test("Step navigation", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test initial state
            assert.equal(component.state.currentStep, 1, "Should start at step 1");
            
            // Test can proceed logic
            component.state.selectedCommits.add(1);
            component.updateCanProceed();
            assert.ok(component.state.canProceed, "Should be able to proceed with selected commits");
            
            // Test next step
            component.state.currentStep = 2;
            component.state.selectedTimesheets.add(1);
            component.updateCanProceed();
            assert.ok(component.state.canProceed, "Should be able to proceed with selected timesheets");
            
            // Test previous step
            component.state.currentStep = 3;
            component.prevStep();
            assert.equal(component.state.currentStep, 2, "Should go back to step 2");
        });

        QUnit.test("Commit domain building", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test empty filters
            let domain = component._buildCommitDomain();
            assert.ok(Array.isArray(domain), "Domain should be an array");
            
            // Test with filters
            component.state.commitFilters.repository = 1;
            component.state.commitFilters.branch = "main";
            component.state.commitFilters.onlyUnmapped = true;
            
            domain = component._buildCommitDomain();
            
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "repository_id"), "Should filter by repository");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "branch_name"), "Should filter by branch");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "is_mapped"), "Should filter by mapping status");
        });

        QUnit.test("Timesheet domain building", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test with filters
            component.state.timesheetFilters.project = 1;
            component.state.timesheetFilters.employee = 2;
            
            const domain = component._buildTimesheetDomain();
            
            assert.ok(Array.isArray(domain), "Domain should be an array");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "project_id"), "Should filter by project");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "employee_id"), "Should filter by employee");
        });

        QUnit.test("Selection management", async function (assert) {
            assert.expect(8);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test commit selection
            component.toggleCommitSelection(1);
            assert.ok(component.state.selectedCommits.has(1), "Commit should be selected");
            
            component.toggleCommitSelection(1);
            assert.ok(!component.state.selectedCommits.has(1), "Commit should be deselected");
            
            // Test select all commits
            component.state.commits = [{id: 1}, {id: 2}, {id: 3}];
            component.selectAllCommits();
            assert.equal(component.state.selectedCommits.size, 3, "All commits should be selected");
            
            component.deselectAllCommits();
            assert.equal(component.state.selectedCommits.size, 0, "All commits should be deselected");
            
            // Test timesheet selection
            component.toggleTimesheetSelection(1);
            assert.ok(component.state.selectedTimesheets.has(1), "Timesheet should be selected");
            
            component.toggleTimesheetSelection(1);
            assert.ok(!component.state.selectedTimesheets.has(1), "Timesheet should be deselected");
            
            // Test select all timesheets
            component.state.timesheets = [{id: 1}, {id: 2}, {id: 3}];
            component.selectAllTimesheets();
            assert.equal(component.state.selectedTimesheets.size, 3, "All timesheets should be selected");
            
            component.deselectAllTimesheets();
            assert.equal(component.state.selectedTimesheets.size, 0, "All timesheets should be deselected");
        });

        QUnit.test("Sequential mapping generation", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Setup test data
            component.state.selectedCommits = new Set([1, 2, 3]);
            component.state.selectedTimesheets = new Set([10, 20]);
            
            component.generateSequentialMappings();
            
            assert.equal(component.state.previewMappings.length, 3, "Should create 3 mappings");
            assert.equal(component.state.previewMappings[0].commit_id, 1, "First mapping should be commit 1");
            assert.equal(component.state.previewMappings[0].timesheet_id, 10, "First mapping should be timesheet 10");
        });

        QUnit.test("Manual mapping addition", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test adding manual mapping
            component.addManualMapping(1, 10);
            
            assert.equal(component.state.previewMappings.length, 1, "Should have one mapping");
            assert.equal(component.state.previewMappings[0].commit_id, 1, "Mapping should have correct commit");
            assert.equal(component.state.previewMappings[0].timesheet_id, 10, "Mapping should have correct timesheet");
        });

        QUnit.test("Mapping preview removal", async function (assert) {
            assert.expect(2);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Setup test mappings
            component.state.previewMappings = [
                {commit_id: 1, timesheet_id: 10},
                {commit_id: 2, timesheet_id: 20},
            ];
            
            component.removeMappingPreview(0);
            
            assert.equal(component.state.previewMappings.length, 1, "Should have one mapping left");
            assert.equal(component.state.previewMappings[0].commit_id, 2, "Remaining mapping should be commit 2");
        });

        QUnit.test("Progress calculation", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test initial state
            assert.equal(component.getProgressPercentage(), 0, "Initial progress should be 0");
            
            // Test with progress
            component.state.totalToProcess = 10;
            component.state.processedCount = 5;
            
            assert.equal(component.getProgressPercentage(), 50, "Progress should be 50%");
            
            component.state.processedCount = 10;
            assert.equal(component.getProgressPercentage(), 100, "Progress should be 100%");
        });

        QUnit.test("Utility functions", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test confidence class
            assert.equal(component.getConfidenceClass(85), "text-success", "High confidence should be success");
            assert.equal(component.getConfidenceClass(65), "text-warning", "Medium confidence should be warning");
            assert.equal(component.getConfidenceClass(45), "text-danger", "Low confidence should be danger");
            
            // Test duration formatting
            const formatted = component.formatDuration(65000); // 1 minute 5 seconds
            assert.ok(formatted.includes("1m") && formatted.includes("5s"), "Should format duration correctly");
        });

        QUnit.test("Default date range", async function (assert) {
            assert.expect(2);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            const dateFrom = component._getDefaultDateFrom();
            const dateTo = component._getDefaultDateTo();
            
            assert.ok(typeof dateFrom === "string", "Date from should be a string");
            assert.ok(typeof dateTo === "string", "Date to should be a string");
        });

        QUnit.test("Drag and drop handling", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new BulkMappingComponent(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test drag start
            const mockEvent = {
                dataTransfer: {
                    effectAllowed: null,
                    setData: function(type, data) {
                        this.data = data;
                    }
                }
            };
            
            component.onCommitDragStart(mockEvent, 123);
            assert.equal(component.state.draggedCommit, 123, "Dragged commit should be set");
            
            // Test drag over
            const dragOverEvent = {
                preventDefault: function() {
                    this.defaultPrevented = true;
                }
            };
            
            component.onTimesheetDragOver(dragOverEvent, 456);
            assert.equal(component.state.dropTarget, 456, "Drop target should be set");
            
            // Test drag end
            component.onDragEnd();
            assert.equal(component.state.draggedCommit, null, "Dragged commit should be cleared");
        });
    });
});
