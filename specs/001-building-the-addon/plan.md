# Implementation Plan: Git Repository Commit to Timesheet Mapping Addon


**Branch**: `001-building-the-addon` | **Date**: September 13, 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-building-the-addon/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Git Repository Commit to Timesheet Mapping Addon for Odoo 18.0 that enables users to connect GitHub/GitLab repositories, fetch commits, and map them to project timesheets with bulk operations and duplicate prevention. Primary requirement is seamless integration with existing Odoo project/timesheet modules using standard Odoo addon architecture and Python/XML technical stack.

## Technical Context
**Language/Version**: Python 3.10+ (Odoo 18.0 requirement)  
**Primary Dependencies**: Odoo 18.0-20250807, PyGithub, python-gitlab, requests, python-dateutil  
**Storage**: PostgreSQL (Odoo standard database)  
**Testing**: Odoo test framework, unittest, pytest  
**Target Platform**: Odoo server environment (Linux/Windows/macOS)
**Project Type**: single (Odoo addon)  
**Performance Goals**: Handle 1000+ commits efficiently, <5s repository connection time  
**Constraints**: Must integrate with existing Odoo security model, follow Odoo MVC patterns  
**Scale/Scope**: Support multiple repositories per instance, 100+ users, enterprise-ready
**Additional Context**: use the tech stack that is required by Odoo 18.0-20250807 for custom addons

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 1 (Odoo addon structure)
- Using framework directly? (yes - Odoo ORM, web framework directly)
- Single data model? (yes - repository connections, commits, mappings)
- Avoiding patterns? (using Odoo MVC pattern as required by platform)

**Architecture**:
- EVERY feature as library? (Odoo addon modules serve as libraries)
- Libraries listed: git_timesheet_mapper (main addon module)
- CLI per library: Odoo CLI integration via odoo-bin
- Library docs: Follow Odoo documentation standards

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (yes)
- Git commits show tests before implementation? (will enforce)
- Order: Contract→Integration→E2E→Unit strictly followed? (yes)
- Real dependencies used? (yes - actual Odoo database, real Git APIs)
- Integration tests for: new models, API integrations, UI components
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging included? (yes - Odoo logging framework)
- Frontend logs → backend? (yes - Odoo unified logging)
- Error context sufficient? (yes - comprehensive error handling)

**Versioning**:
- Version number assigned? (1.0.0)
- BUILD increments on every change? (yes)
- Breaking changes handled? (migration scripts, backward compatibility)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Odoo Addon Structure (Standard)
git_timesheet_mapper/
├── __manifest__.py         # Addon manifest
├── models/
│   ├── __init__.py
│   ├── git_repository.py   # Repository connection model
│   ├── git_commit.py       # Commit tracking model
│   └── timesheet_mapping.py # Commit-timesheet mapping
├── controllers/
│   ├── __init__.py
│   └── git_api.py          # API endpoints for Git operations
├── views/
│   ├── git_repository_views.xml
│   ├── git_commit_views.xml
│   └── timesheet_mapping_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── data.xml
├── static/
│   └── src/
│       ├── js/
│       ├── css/
│       └── xml/
├── wizard/
│   ├── __init__.py
│   └── bulk_mapping_wizard.py
└── tests/
    ├── __init__.py
    ├── test_git_repository.py
    ├── test_git_commit.py
    ├── test_timesheet_mapping.py
    └── test_bulk_operations.py
```

**Structure Decision**: Odoo addon structure as required by Odoo 18.0 standards

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/bash/update-agent-context.sh copilot` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base structure
- Generate tasks from Phase 1 design docs (data-model.md, api-contracts.md, quickstart.md)
- Each API endpoint → contract test task [P]
- Each model (git.repository, git.commit, timesheet.commit.mapping) → model creation task [P]
- Each user story from spec → integration test task
- Implementation tasks organized by TDD principles

**Task Categories**:
1. **Model Development**: Create Odoo models with fields, constraints, and methods
2. **API Implementation**: Build controllers for Git API integration and web endpoints
3. **User Interface**: Develop views, wizards, and JavaScript components
4. **Integration Tests**: Validate Git API connections and timesheet mappings
5. **Security & Permissions**: Implement access controls and data encryption

**Ordering Strategy**:
- TDD order: Contract tests → Integration tests → Unit tests → Implementation
- Dependency order: Models → Services → Controllers → Views → Wizards
- Parallel execution marked [P] for independent components

**Estimated Output**: 35-40 numbered, ordered tasks covering:
- 8 contract test tasks for API endpoints
- 6 model creation tasks for core entities
- 12 implementation tasks for business logic
- 8 UI/UX tasks for views and wizards
- 6 integration and validation tasks

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*