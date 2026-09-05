# Testing Strategy & Implementation

## Test Pyramid

```
                    E2E Tests (Playwright)
                   /                        \
            Integration Tests (API)       UI Component Tests
           /              |              \
      Unit Tests     Unit Tests        Unit Tests
     (Backend)       (Frontend)      (Shared Utils)
```

## Test Coverage Goals

| Layer | Target Coverage | Tools |
|-------|----------------|-------|
| Backend Unit | > 85% | pytest, pytest-asyncio, pytest-mock |
| Backend Integration | > 70% | pytest, httpx, testcontainers |
| API Contract | 100% endpoints | pytest, pydantic validation |
| Frontend Unit | > 80% | Vitest, React Testing Library |
| E2E | Critical paths | Playwright |

---

## Backend Tests

### Structure
```
backend/tests/
├── conftest.py              # Fixtures & configuration
├── test_api.py              # API endpoint tests
├── test_contracts.py        # API contract validation
├── test_services.py         # Service layer tests
├── test_agents.py           # AI agent tests
├── test_scanners.py         # Security scanner tests
└── test_utils.py            # Utility tests
```

### Running Backend Tests
```bash
cd backend
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest --cov=./ --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_api.py -v

# Run with specific markers
pytest -m "not slow" -v

# Run with database
pytest --db=postgresql
```

### Key Fixtures (conftest.py)
- `test_engine` - In-memory SQLite for fast tests
- `db_session` - Transactional session per test
- `client` - Async HTTP client with dependency overrides
- `test_user` / `admin_user` - Pre-created users
- `auth_headers` / `admin_auth_headers` - JWT auth
- `test_repository` - Pre-created repo with CLONED status
- `test_scan` - Completed scan with findings
- `test_findings` - Multiple findings (HIGH, MEDIUM)
- `test_patch` - Generated patch in GENERATED status

---

## Frontend Tests

### Structure
```
frontend/tests/
├── fixtures.ts              # Playwright fixtures with auth
├── utils.ts                 # Test utilities & helpers
├── test-utils.ts            # Shared test functions
├── auth.spec.ts             # Authentication flows
├── dashboard.spec.ts        # Dashboard & repositories
├── scans.spec.ts            # Scan management
├── findings.spec.ts         # Findings list & detail
├── patches.spec.ts          # Patch generation & verification
├── chat.spec.ts             # Chat assistant
├── github.spec.ts           # GitHub integration
└── test-utils.ts            # Shared utilities
```

### Running Frontend Tests
```bash
cd frontend

# Unit tests
npm run test -- --run

# Type checking
npx tsc --noEmit

# Linting
npm run lint

# E2E tests (requires running app)
npm run dev &          # Start dev server
npx playwright test    # Run Playwright tests

# Specific test file
npx playwright test tests/auth.spec.ts

# Headed mode for debugging
npx playwright test --headed

# Debug mode
npx playwright test --debug
```

### Playwright Fixtures (fixtures.ts)
- `authenticatedPage` - Page with logged-in user
- `apiRequest` - Direct API request context
- `testUser` - Auto-created test user
- `testRepository` - Repository via GitHub API
- `testScan` - Scan with findings
- `testFinding` - Finding with all metadata
- `testPatch` - Patch in GENERATED status

---

## API Contract Tests

### Test Coverage
- **Response schemas** - All Pydantic models validated
- **Request validation** - 422 errors for invalid input
- **Error formats** - Consistent error structure
- **Headers** - CORS, content-type, process-time
- **Pagination** - Consistent pagination structure

### Schema Validation
```python
# Every endpoint response validated against Pydantic model
user = UserResponse(**response.json())
scan = ScanResponse(**response.json())
finding = FindingResponse(**response.json())
```

---

## E2E Test Scenarios

### Authentication Flow
1. User registration with validation
2. Login with JWT token storage
3. Token refresh flow
4. Protected route redirects
4. Logout & token cleanup

### Repository Management
1. Add repository via GitHub URL
2. URL validation (GitHub only)
3. Clone & language detection
4. Repository listing & filtering
5. Delete repository

### Scan Management
1. Create scan (full/incremental/PR)
2. Scan status tracking
3. Scan cancellation
4. Scan retry
5. Summary statistics

### Findings Workflow
1. List with filters (severity, status, scanner)
2. Search by keyword
3. Finding detail view
4. AI explanation on demand
5. Status updates (fixed, ignored, FP)
6. Bulk operations

### Patch Generation & Verification
1. Generate patch from finding
2. View diff with syntax highlighting
3. Apply patch with git
3. Run test suite
4. Security re-scan
5. Auto-retry on failure
6. Alternative strategies

### Chat Assistant
1. Send/receive messages
2. Context badges (repo, scan, finding)
3. Suggestion chips
4. Loading states
5. Copy to clipboard
6. Markdown rendering

### GitHub Integration
1. OAuth flow
2. Installation management
3. Repository import
4. PR creation from patches
5. PR status sync

---

## CI/CD Pipeline

### GitHub Actions Workflow (`.github/workflows/tests.yml`)

```yaml
jobs:
  backend-tests:     # pytest + coverage
  frontend-tests:    # vitest + lint + typecheck
  playwright-tests:  # Full E2E with real services
  security-scan:     # Trivy, Semgrep, Bandit, TruffleHog
  docker-build:      # Multi-stage build test
  deploy-staging:    # Auto-deploy main to staging
  deploy-production: # Manual production deploy
```

### Service Containers
- PostgreSQL 16
- Redis 7
- ChromaDB 0.4

### Parallel Execution
- Backend & frontend tests run in parallel
- Playwright runs after unit tests pass
- Security scans run independently

---

## Test Data Management

### Database Seeding
```python
# conftest.py creates test data per test session
# Transaction rollback after each test
# No test pollution
```

### API Mocking
```python
# Playwright fixtures use real API
# Can be swapped with MSW for unit tests
```

---

## Performance Testing

### Load Testing Targets
- API response < 200ms (p95)
- Scan initiation < 5s
- Patch generation < 30s
- Report generation < 10s

### Tools
- Locust for load testing
- k6 for API stress testing
- Playwright for frontend perf

---

## Debugging Tests

### Backend
```bash
# Run single test with output
pytest tests/test_api.py::TestAuthEndpoints::test_login -v -s

# Debug with pdb
pytest tests/test_api.py::TestAuthEndpoints::test_login --pdb

# Verbose SQL
DATABASE_ECHO=true pytest tests/test_api.py
```

### Frontend
```bash
# Debug specific test
npx playwright test tests/auth.spec.ts --debug

# Headed mode
npx playwright test tests/auth.spec.ts --headed

# Trace viewer
npx playwright show-trace trace.zip
```

### Playwright Trace
```typescript
// Auto-captured on failure
// View: npx playwright show-trace trace.zip
```

---

## Test Reports

### Coverage Reports
- Backend: `backend/htmlcov/index.html`
- Frontend: `frontend/coverage/index.html`

### Test Results
- JUnit XML: `test-results.xml`
- Playwright HTML: `playwright-report/index.html`
- Allure: `allure-report/index.html` (optional)

### CI Artifacts
- Coverage XML (Codecov)
- Playwright HTML report
- Test results JSON/XML
- Screenshots/videos on failure

---

## Best Practices

### Test Organization
- One test file per feature/module
- Descriptive test names: `should_<action>_when_<condition>`
- AAA pattern: Arrange, Act, Assert
- Shared fixtures in conftest.py

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_function(client: AsyncClient):
    response = await client.get("/endpoint")
    assert response.status_code == 200
```

### Database Isolation
```python
# Each test gets fresh session
# Automatic rollback after test
# No manual cleanup needed
```

### Frontend Test IDs
```tsx
// Use data-testid for stable selectors
<button data-testid="submit-button">Submit</button>

// In test:
await page.locator('[data-testid="submit-button"]').click()
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Database locked | Use `:memory:` SQLite or separate test DB |
| Port conflicts | Use random ports or Docker |
| Flaky E2E | Add retries, increase timeouts |
| Slow tests | Parallel execution, mock external APIs |
| Token expiry | Auto-refresh in fixtures |

### Debug Commands
```bash
# Check test database
sqlite3 test.db ".schema"

# View API requests
npx playwright test --trace on

# Profile test duration
pytest --durations=10
```