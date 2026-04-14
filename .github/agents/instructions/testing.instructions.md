---
applyTo: "services/*/tests/**/*.py,tests/**/*.py"
---

# Testing Conventions

## Framework
- `pytest` + `pytest-asyncio` (mode=auto)
- `httpx.AsyncClient` for API tests
- `factory_boy` for test data
- `respx` for mocking HTTP (LLM, external APIs)
- `testcontainers` for integration tests with real DB

## File Organization
```
services/<name>/tests/
├── conftest.py          # Shared fixtures
├── factories.py         # Factory Boy definitions
├── unit/
│   ├── test_services.py
│   └── test_utils.py
└── integration/
    ├── test_api.py
    └── test_repos.py
```

## Fixture Patterns

### DB Session (Transaction Rollback)
```python
@pytest.fixture
async def db_session(engine):
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)
        yield session
        await trans.rollback()
```

### API Client
```python
@pytest.fixture
async def api_client(app, db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

### Auth Headers
```python
@pytest.fixture
def student_headers():
    token = create_access_token(user_id=uuid4(), roles=["student"])
    return {"Authorization": f"Bearer {token}"}
```

## Test Rules
- Every test function must be `async def` and use `pytest.mark.asyncio`
- Use fixtures for setup — never create data inline
- Test both happy path and error paths
- Test authorization: correct role succeeds, wrong role → 403, no token → 401
- Test validation: missing fields → 422 with details
- Assert on specific status codes and response structure
- Use `factory_boy` sequences to avoid unique constraint violations

## Naming
- Test files: `test_<module>.py`
- Test functions: `test_<action>_<scenario>` (e.g., `test_create_course_success`, `test_create_course_missing_title`)

## Coverage
- Target: >80% per service
- Run: `pytest --cov=app --cov-report=term-missing`
- Exclude: `alembic/`, `__main__.py`

## Markers
```ini
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests requiring infrastructure",
    "unit: marks unit tests",
]
```
