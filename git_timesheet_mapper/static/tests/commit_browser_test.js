/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GitCommitBrowser } from "@git_timesheet_mapper/js/commit_browser";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("Git Timesheet Mapper", {}, function () {
    QUnit.module("GitCommitBrowser Component", {}, function () {
        
        QUnit.test("Component initialization", async function (assert) {
            assert.expect(2);
            
            const component = new GitCommitBrowser();
            assert.ok(component, "Component should be created");
            assert.equal(component.constructor.name, "GitCommitBrowser", "Component should be GitCommitBrowser");
        });

        QUnit.test("State initialization", async function (assert) {
            assert.expect(5);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            assert.ok(component.state, "State should be initialized");
            assert.equal(component.state.currentView, "repositories", "Initial view should be repositories");
            assert.ok(Array.isArray(component.state.repositories), "Repositories should be an array");
            assert.ok(Array.isArray(component.state.commits), "Commits should be an array");
            assert.ok(component.state.selectedCommits instanceof Set, "Selected commits should be a Set");
        });

        QUnit.test("Filter functionality", async function (assert) {
            assert.expect(3);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test filter building
            component.state.filters.repository = 1;
            component.state.filters.branch = "main";
            component.state.filters.onlyUnmapped = true;
            
            const domain = component._buildCommitDomain();
            
            assert.ok(Array.isArray(domain), "Domain should be an array");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "repository_id"), "Should filter by repository");
            assert.ok(domain.some(d => Array.isArray(d) && d[0] === "is_mapped"), "Should filter by mapping status");
        });

        QUnit.test("Commit selection", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Test commit selection
            component.toggleCommitSelection(1);
            assert.ok(component.state.selectedCommits.has(1), "Commit should be selected");
            
            component.toggleCommitSelection(1);
            assert.ok(!component.state.selectedCommits.has(1), "Commit should be deselected");
            
            // Test select all
            component.state.commits = [{id: 1}, {id: 2}, {id: 3}];
            component.selectAllVisible();
            assert.equal(component.state.selectedCommits.size, 3, "All commits should be selected");
            
            // Test clear selection
            component.clearSelection();
            assert.equal(component.state.selectedCommits.size, 0, "Selection should be cleared");
        });

        QUnit.test("Search functionality", async function (assert) {
            assert.expect(2);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            component.state.commits = [
                {id: 1, commit_message_short: "Fix bug in login", author_name: "John Doe"},
                {id: 2, commit_message_short: "Add new feature", author_name: "Jane Smith"},
                {id: 3, commit_message_short: "Update documentation", author_name: "John Doe"},
            ];
            
            component.state.searchQuery = "bug";
            component.performSearch();
            
            assert.equal(component.state.filteredCommits.length, 1, "Should find one commit with 'bug'");
            
            component.state.searchQuery = "John";
            component.performSearch();
            
            assert.equal(component.state.filteredCommits.length, 2, "Should find two commits by John");
        });

        QUnit.test("Pagination", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            // Create test commits
            const commits = [];
            for (let i = 1; i <= 25; i++) {
                commits.push({id: i, commit_message_short: `Commit ${i}`});
            }
            component.state.filteredCommits = commits;
            component.state.itemsPerPage = 10;
            
            component.updatePagination();
            
            assert.equal(component.state.totalPages, 3, "Should have 3 pages");
            assert.equal(component.state.paginatedCommits.length, 10, "Should show 10 items per page");
            
            component.goToPage(2);
            assert.equal(component.state.currentPage, 2, "Should be on page 2");
            assert.equal(component.state.paginatedCommits[0].id, 11, "First item on page 2 should be commit 11");
        });

        QUnit.test("Date formatting", async function (assert) {
            assert.expect(2);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            const testDate = "2024-01-15T10:30:00Z";
            const formatted = component.formatDate(testDate);
            
            assert.ok(typeof formatted === "string", "Should return a string");
            assert.ok(formatted.length > 0, "Should not be empty");
        });

        QUnit.test("Commit type badge class", async function (assert) {
            assert.expect(4);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
                env,
                props: {},
            });
            
            await component.setup();
            
            assert.equal(component.getCommitTypeBadgeClass("feature"), "success", "Feature should be success");
            assert.equal(component.getCommitTypeBadgeClass("bugfix"), "danger", "Bugfix should be danger");
            assert.equal(component.getCommitTypeBadgeClass("refactor"), "warning", "Refactor should be warning");
            assert.equal(component.getCommitTypeBadgeClass("unknown"), "light", "Unknown should be light");
        });

        QUnit.test("Drag and drop setup", async function (assert) {
            assert.expect(2);
            
            const env = await makeTestEnv();
            const component = new GitCommitBrowser(null, {
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
            assert.equal(mockEvent.dataTransfer.effectAllowed, "move", "Effect should be move");
        });
    });
});
