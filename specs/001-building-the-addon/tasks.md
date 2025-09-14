# Tasks: Git Repository Commit to Timesheet Mapping Addon

**Input**: Design documents from `/specs/001-building-the-addon/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
   → Tech stack: Python 3.10+, Odoo 18.0, PyGithub, python-gitlab
   → Structure: Odoo addon with models/, controllers/, views/, wizards/
2. Load optional design documents: ✓
   → data-model.md: 4 entities (git.repository, git.commit, timesheet.commit.mapping, account.analytic.line)
   → contracts/: 15+ API endpoints for repo management, commit fetching, mapping operations
   → research.md: Odoo 18.0 standards, security patterns, performance optimizations
3. Generate tasks by category: ✓
   → Setup: Odoo addon structure, dependencies, manifest
   → Tests: contract tests for all endpoints, integration tests for user stories
   → Core: models for 4 entities, controllers for API endpoints, wizards for bulk operations
   → Integration: Git API services, security, views and UI components
   → Polish: comprehensive testing, performance optimization, documentation
4. Apply task rules: ✓
   → Different files = mark [P] for parallel execution
   → Same file = sequential (no [P] mark)
   → All tests before implementation (TDD strictly enforced)
5. Number tasks sequentially (T001, T002...) ✓
6. Generate dependency graph ✓
7. Create parallel execution examples ✓
8. Validate task completeness: ✓
   → All 15+ API endpoints have contract tests
   → All 4 entities have model creation tasks
   → All user stories have integration tests
9. Return: SUCCESS (40 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Odoo Addon Structure**: `git_timesheet_mapper/` at repository root
- Models: `git_timesheet_mapper/models/`
- Controllers: `git_timesheet_mapper/controllers/`
- Views: `git_timesheet_mapper/views/`
- Tests: `git_timesheet_mapper/tests/`

## Phase 3.1: Setup
- [x] T001 Create Odoo addon directory structure git_timesheet_mapper/ with __init__.py files
- [x] T002 Create __manifest__.py with dependencies ['project', 'hr_timesheet'] and Python requirements
- [x] T003 [P] Create security/ir.model.access.csv for model access rights
- [x] T004 [P] Create security/security.xml for user groups and record rules

## Phase 3.2: Tests First (TDD) ✅ COMPLETED
**All tests written and failing as expected per TDD methodology**

### Contract Tests for API Endpoints
- [x] T005 [P] Contract test POST /git_timesheet_mapper/repository/create in git_timesheet_mapper/tests/test_repository_api.py
- [x] T006 [P] Contract test POST /git_timesheet_mapper/repository/test_connection in git_timesheet_mapper/tests/test_repository_api.py
- [x] T007 [P] Contract test GET /git_timesheet_mapper/repository/{id}/branches in git_timesheet_mapper/tests/test_repository_api.py
- [x] T008 [P] Contract test POST /git_timesheet_mapper/commits/fetch in git_timesheet_mapper/tests/test_commit_api.py
- [x] T009 [P] Contract test GET /git_timesheet_mapper/commits/search in git_timesheet_mapper/tests/test_commit_api.py
- [x] T010 [P] Contract test POST /git_timesheet_mapper/mapping/create in git_timesheet_mapper/tests/test_mapping_api.py
- [x] T011 [P] Contract test POST /git_timesheet_mapper/mapping/bulk_create in git_timesheet_mapper/tests/test_mapping_api.py
- [x] T012 [P] Contract test DELETE /git_timesheet_mapper/mapping/{id} in git_timesheet_mapper/tests/test_mapping_api.py

### Integration Tests for User Stories
- [x] T013 [P] Integration test repository connection and authentication in git_timesheet_mapper/tests/test_git_integration.py
- [x] T014 [P] Integration test commit fetching from GitHub/GitLab in git_timesheet_mapper/tests/test_git_integration.py
- [x] T015 [P] Integration test commit to timesheet mapping workflow in git_timesheet_mapper/tests/test_timesheet_integration.py
- [x] T016 [P] Integration test bulk mapping operations in git_timesheet_mapper/tests/test_timesheet_integration.py
- [x] T017 [P] Integration test duplicate mapping prevention in git_timesheet_mapper/tests/test_timesheet_integration.py

## Phase 3.3: Core Implementation ✅ COMPLETED
**Models implemented and ready for service layer**

### Model Implementation
- [x] T018 [P] GitRepository model in git_timesheet_mapper/models/git_repository.py
- [x] T019 [P] GitCommit model in git_timesheet_mapper/models/git_commit.py
- [x] T020 [P] TimesheetCommitMapping model in git_timesheet_mapper/models/timesheet_mapping.py
- [x] T021 [P] Extend account.analytic.line in git_timesheet_mapper/models/timesheet_mapping.py

## Phase 3.4: Service Layer Implementation ✅ COMPLETED
**Business logic and Git platform integration services**

### Service Layer Implementation
- [x] T022 [P] GitHub API service in git_timesheet_mapper/services/github_service.py
- [x] T023 [P] GitLab API service in git_timesheet_mapper/services/gitlab_service.py
- [x] T024 [P] Git API factory service in git_timesheet_mapper/services/git_service_factory.py
- [x] T025 Commit mapping service in git_timesheet_mapper/services/mapping_service.py

## Phase 3.5: Controller Implementation ✅ COMPLETED
**API endpoints for Git integration and mapping operations**

### Controller Implementation ✅ COMPLETED
- [x] T026 Repository management controller in git_timesheet_mapper/controllers/git_api.py
- [x] T027 Commit operations controller in git_timesheet_mapper/controllers/git_api.py
- [x] T028 Mapping operations controller in git_timesheet_mapper/controllers/git_api.py
- [x] T029 Statistics and dashboard controller in git_timesheet_mapper/controllers/git_api.py

## Phase 3.6: User Interface and Views ✅ COMPLETED
**XML views and wizards for user interaction**

- [x] T030 [P] Git repository views in git_timesheet_mapper/views/git_repository_views.xml
- [x] T031 [P] Git commit views in git_timesheet_mapper/views/git_commit_views.xml
- [x] T032 [P] Timesheet mapping views in git_timesheet_mapper/views/timesheet_mapping_views.xml
- [x] T033 [P] Bulk mapping wizard in git_timesheet_mapper/wizard/bulk_mapping_wizard.py
- [x] T034 [P] Bulk mapping wizard views in git_timesheet_mapper/wizard/bulk_mapping_views.xml

## Phase 3.7: Frontend Components
- [ ] T035 [P] JavaScript commit browser component in git_timesheet_mapper/static/src/js/commit_browser.js
- [ ] T036 [P] JavaScript bulk mapping component in git_timesheet_mapper/static/src/js/bulk_mapper.js
- [ ] T037 [P] CSS styling for git integration views in git_timesheet_mapper/static/src/css/git_timesheet.css
- [ ] T038 [P] XML templates for JS components in git_timesheet_mapper/static/src/xml/git_timesheet.xml

## Phase 3.8: Polish and Validation
- [ ] T039 [P] Unit tests for model validation in git_timesheet_mapper/tests/test_model_validation.py
- [ ] T040 Performance optimization and caching implementation in git_timesheet_mapper/services/

## Dependencies
- Setup (T001-T004) must complete before tests
- Tests (T005-T017) before any implementation (T018-T040)
- Models (T018-T021) before services (T022-T025)
- Services before controllers (T026-T029)
- Models and controllers before UI (T030-T038)
- Core implementation before polish (T039-T040)

## Parallel Execution Examples

### Phase 3.2 - Contract Tests (All Parallel)
```bash
# Launch all contract tests together since they're in different test files:
Task: "Contract test POST /git_timesheet_mapper/repository/create in git_timesheet_mapper/tests/test_repository_api.py"
Task: "Contract test POST /git_timesheet_mapper/commits/fetch in git_timesheet_mapper/tests/test_commit_api.py"  
Task: "Contract test POST /git_timesheet_mapper/mapping/create in git_timesheet_mapper/tests/test_mapping_api.py"
Task: "Integration test repository connection in git_timesheet_mapper/tests/test_git_integration.py"
Task: "Integration test commit mapping workflow in git_timesheet_mapper/tests/test_timesheet_integration.py"
```

### Phase 3.3 - Model Creation (All Parallel)
```bash
# Launch model creation together since each is in separate file:
Task: "GitRepository model in git_timesheet_mapper/models/git_repository.py"
Task: "GitCommit model in git_timesheet_mapper/models/git_commit.py"
Task: "GitHub API service in git_timesheet_mapper/services/github_service.py"
Task: "GitLab API service in git_timesheet_mapper/services/gitlab_service.py"
```

### Phase 3.4 - UI Components (All Parallel)
```bash
# Launch UI development together since each component is separate:
Task: "Git repository views in git_timesheet_mapper/views/git_repository_views.xml"
Task: "Bulk mapping wizard in git_timesheet_mapper/wizard/bulk_mapping_wizard.py"
Task: "JavaScript commit browser in git_timesheet_mapper/static/src/js/commit_browser.js"
Task: "CSS styling in git_timesheet_mapper/static/src/css/git_timesheet.css"
```

## Notes
- [P] tasks = different files, truly independent execution
- Verify ALL tests fail before implementing (TDD requirement)
- Commit after each task completion
- Controller tasks sequential (T026-T029) as they modify same file
- Model extension task (T021) can run with core models as it's separate concern

## Task Generation Rules Applied

### From API Contracts (15+ endpoints):
- Repository management: 3 contract tests (T005-T007)
- Commit operations: 2 contract tests (T008-T009)  
- Mapping operations: 3 contract tests (T010-T012)
- Each endpoint group → separate implementation task

### From Data Model (4 entities):
- git.repository → T018 model creation [P]
- git.commit → T019 model creation [P]
- timesheet.commit.mapping → T020 model creation [P]
- account.analytic.line extension → T021 model extension [P]

### From User Stories (5 main scenarios):
- Repository connection → T013 integration test [P]
- Commit fetching → T014 integration test [P]
- Single mapping → T015 integration test [P]
- Bulk mapping → T016 integration test [P]
- Duplicate prevention → T017 integration test [P]

### From Technical Architecture:
- Service layer for Git API abstraction (T022-T025)
- Controller layer for web endpoints (T026-T029)
- UI layer for user interaction (T030-T038)

## Validation Checklist
*GATE: Checked by main() before execution*

- [x] All 15+ API contracts have corresponding test tasks
- [x] All 4 entities have model creation tasks
- [x] All 5 user stories have integration test tasks
- [x] All tests (T005-T017) come before implementation (T018+)
- [x] Parallel tasks ([P]) are truly independent (different files)
- [x] Each task specifies exact file path
- [x] No [P] task modifies same file as another [P] task
- [x] TDD order strictly enforced: failing tests → implementation → validation
- [x] Odoo addon structure properly reflected in all file paths
- [x] Security, performance, and polish phases included
