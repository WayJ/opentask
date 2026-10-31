# OpenTask CLI Test Plan

## Test Inventory

- `test_core.py`: 30 unit tests planned
  - API client methods (10 tests)
  - Configuration management (5 tests)
  - Command modules (15 tests)

- `test_full_e2e.py`: 10 E2E tests planned
  - Authentication flow (2 tests)
  - Project CRUD (3 tests)
  - Issue CRUD (3 tests)
  - Integration scenarios (2 tests)

## Unit Test Plan

### API Client Tests (`test_api_client.py`)

1. **test_client_init**: Test client initialization with/without token
2. **test_get_headers**: Test header generation with authentication
3. **test_handle_response_success**: Test successful response handling
4. **test_handle_response_error**: Test error response handling
5. **test_list_projects**: Test project listing
6. **test_get_project**: Test single project retrieval
7. **test_create_project**: Test project creation
8. **test_list_issues**: Test issue listing with filters
9. **test_create_issue**: Test issue creation
10. **test_api_error**: Test APIError exception

### Configuration Tests (`test_config.py`)

1. **test_config_defaults**: Test default configuration values
2. **test_config_set_get**: Test setting and getting values
3. **test_config_persistence**: Test configuration persistence across reloads
4. **test_api_url_property**: Test api_url property
5. **test_token_property**: Test token property
6. **test_active_project**: Test active project context

### Command Tests (`test_commands.py`)

1. **test_project_list**: Test project list command
2. **test_project_create**: Test project creation command
3. **test_project_use**: Test setting active project
4. **test_issue_list**: Test issue list command
5. **test_issue_create**: Test issue creation command
6. **test_issue_update**: Test issue update command
7. **test_issue_status**: Test quick status update
8. **test_json_output**: Test JSON output mode
9. **test_repl_prompt**: Test REPL prompt generation
10. **test_skin_messages**: Test skin message formatting

## E2E Test Plan

### Authentication Flow

1. **test_login_and_me**:
   - Simulates: User login workflow
   - Operations: Login → Get user info → Verify token stored
   - Verified: Token is saved and user info is retrievable

2. **test_logout**:
   - Simulates: User logout
   - Operations: Login → Logout → Verify token cleared
   - Verified: Token is removed from config

### Project CRUD

3. **test_project_lifecycle**:
   - Simulates: Complete project lifecycle
   - Operations: Create → Read → Update → Delete
   - Verified: Project persists through all operations

4. **test_project_list_filtering**:
   - Simulates: Listing with filters
   - Operations: Create multiple projects → List with active_only filter
   - Verified: Correct projects are returned

5. **test_project_context_switching**:
   - Simulates: Switching between projects
   - Operations: Create 2 projects → Use project 1 → Use project 2 → Verify context
   - Verified: Active project context updates correctly

### Issue CRUD

6. **test_issue_lifecycle**:
   - Simulates: Complete issue lifecycle
   - Operations: Create → Read → Update → Delete
   - Verified: Issue persists through all operations

7. **test_issue_with_project_context**:
   - Simulates: Creating issues with active project
   - Operations: Set active project → Create issue → Verify project_id
   - Verified: Issue is associated with active project

8. **test_issue_filtering**:
   - Simulates: Listing issues with filters
   - Operations: Create issues with different statuses → Filter by status
   - Verified: Correct issues are returned

### Integration Scenarios

9. **test_full_workflow**:
   - Simulates: Real-world usage scenario
   - Operations:
     - Login
     - Create project
     - Set active project
     - Create issues
     - Update issue status
     - Add comments
     - List issues
   - Verified: Complete workflow executes without errors

10. **test_json_agent_mode**:
    - Simulates: AI agent using JSON mode
    - Operations:
      - All commands with --json flag
      - Verify JSON output is valid
      - Verify data structure
    - Verified: All commands return valid JSON

## Test Data

### Mock Data

- **Projects**: 3-5 projects with various names and descriptions
- **Issues**: 10-15 issues with different types, statuses, priorities
- **Users**: 2-3 test users for assignment

### Real Data (E2E)

- Tests will create real data in test database
- Each test should clean up after itself
- Use unique names to avoid conflicts

## Success Criteria

- All unit tests pass (100%)
- All E2E tests pass (100%)
- Code coverage > 80%
- No test dependencies (tests can run in any order)
- Tests complete in < 60 seconds

## Test Execution

```bash
# Unit tests only
pytest tests/test_core.py -v

# E2E tests (requires running backend)
pytest tests/test_full_e2e.py -v

# All tests with coverage
pytest tests/ -v --cov=opentask --cov-report=html

# Run specific test
pytest tests/test_core.py::test_api_client::test_list_projects -v
```

## Test Results

*Results will be appended here after test execution*
