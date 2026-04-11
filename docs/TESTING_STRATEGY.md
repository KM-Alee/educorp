# EduCorp — Testing Strategy

## 1. Testing Pyramid

```
                    ┌─────────┐
                    │  E2E /  │   ← Few, expensive, integrated
                    │  Manual │
                   ─┴─────────┴─
                  ┌─────────────┐
                  │ Integration │   ← Cross-service, DB, Kafka
                 ─┴─────────────┴─
                ┌─────────────────┐
                │     Unit        │   ← Fast, isolated, numerous
                └─────────────────┘
```

| Layer | Ratio | Scope | Speed | Tools |
|-------|-------|-------|-------|-------|
| Unit | 70% | Single function/class | <1s per test | pytest, unittest.mock |
| Integration | 20% | Service + DB/Redis/Kafka | <5s per test | pytest, testcontainers, httpx |
| E2E / Manual | 10% | Multi-service workflows | Minutes | Manual scripts, pytest + docker compose |

## 2. Tools & Libraries

| Tool | Purpose |
|------|---------|
| **pytest** | Test runner and framework |
| **pytest-asyncio** | Async test support for FastAPI |
| **pytest-cov** | Coverage reporting |
| **httpx** | Async HTTP client for API testing |
| **factory_boy** | Test data factories |
| **faker** | Realistic fake data generation |
| **testcontainers** | Ephemeral Docker containers for integration tests |
| **respx** | Mock HTTP responses (for LLM API calls) |
| **pytest-mock** | Mocking utilities |
| **locust** | Load/stress testing |

## 3. Test Organization

```
services/auth/
├── tests/
│   ├── conftest.py              # Shared fixtures (db, client, factories)
│   ├── factories.py             # Factory Boy factories for test data
│   ├── unit/
│   │   ├── test_password.py     # Password hashing, validation
│   │   ├── test_jwt.py          # Token creation, validation
│   │   └── test_rbac.py         # Role checks
│   ├── integration/
│   │   ├── test_register.py     # Registration flow with DB
│   │   ├── test_login.py        # Login flow with DB
│   │   ├── test_refresh.py      # Token refresh with DB
│   │   └── test_users_admin.py  # Admin user management
│   └── conftest.py
```

## 4. Test Fixtures

### 4.1 Database Fixture (per-test isolation)

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def db_session():
    """Create a test database session with transaction rollback."""
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

### 4.2 API Client Fixture

```python
@pytest.fixture
async def client(db_session):
    """Create test HTTP client with overridden dependencies."""
    from app.main import app
    from app.dependencies import get_db

    app.dependency_overrides[get_db] = lambda: db_session

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

### 4.3 Authentication Fixtures

```python
@pytest.fixture
def auth_headers(student_user):
    """Generate valid JWT headers for a student."""
    token = create_access_token(
        data={"sub": str(student_user.id), "roles": ["student"]},
        expires_delta=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Generate valid JWT headers for an admin."""
    token = create_access_token(
        data={"sub": str(admin_user.id), "roles": ["admin"]},
        expires_delta=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def instructor_headers(instructor_user):
    """Generate valid JWT headers for an instructor."""
    token = create_access_token(
        data={"sub": str(instructor_user.id), "roles": ["instructor"]},
        expires_delta=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}
```

### 4.4 Factory Boy Factories

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None  # Set in conftest

    id = factory.LazyFunction(uuid4)
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password_hash = factory.LazyFunction(lambda: hash_password("TestPass123!"))
    is_active = True
    is_verified = True


class CourseFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Course

    id = factory.LazyFunction(uuid4)
    title = factory.Faker("sentence", nb_words=4)
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    description = factory.Faker("paragraph")
    category = factory.Faker("random_element", elements=["CS", "Math", "Physics"])
    difficulty = factory.Faker("random_element", elements=["beginner", "intermediate", "advanced"])
    visibility = "DRAFT"


class EnrollmentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Enrollment

    id = factory.LazyFunction(uuid4)
    status = "ENROLLED"
```

## 5. Unit Tests

### 5.1 Test Patterns

```python
# tests/unit/test_password.py

class TestPasswordHashing:
    def test_hash_password_produces_argon2_hash(self):
        hashed = hash_password("TestPass123!")
        assert hashed.startswith("$argon2")

    def test_verify_correct_password(self):
        hashed = hash_password("TestPass123!")
        assert verify_password("TestPass123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("TestPass123!")
        assert verify_password("WrongPass!", hashed) is False

    def test_password_validation_rejects_short(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@b.com", password="short", first_name="A", last_name="B")

    def test_password_validation_accepts_valid(self):
        user = UserCreate(email="a@b.com", password="ValidPass1!", first_name="A", last_name="B")
        assert user.password == "ValidPass1!"
```

### 5.2 Business Logic Tests

```python
# tests/unit/test_enrollment_logic.py

class TestPrerequisiteCheck:
    def test_no_prerequisites_passes(self):
        result = check_prerequisites(course_prerequisites=[], completed_courses=[])
        assert result.passed is True

    def test_met_prerequisites_passes(self):
        result = check_prerequisites(
            course_prerequisites=[uuid1, uuid2],
            completed_courses=[uuid1, uuid2, uuid3],
        )
        assert result.passed is True

    def test_unmet_prerequisites_fails(self):
        result = check_prerequisites(
            course_prerequisites=[uuid1, uuid2],
            completed_courses=[uuid1],
        )
        assert result.passed is False
        assert uuid2 in result.missing

class TestCapacityCheck:
    def test_unlimited_capacity_passes(self):
        assert check_capacity(max_capacity=None, current_count=1000) is True

    def test_under_capacity_passes(self):
        assert check_capacity(max_capacity=100, current_count=99) is True

    def test_at_capacity_fails(self):
        assert check_capacity(max_capacity=100, current_count=100) is False
```

## 6. Integration Tests

### 6.1 API Integration Tests

```python
# tests/integration/test_register.py

class TestRegistration:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "TestPass123!",
            "first_name": "Jane",
            "last_name": "Doe",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["email"] == "new@example.com"
        assert data["roles"] == ["student"]
        assert data["is_verified"] is False

    async def test_register_duplicate_email(self, client, student_user):
        resp = await client.post("/api/v1/auth/register", json={
            "email": student_user.email,
            "password": "TestPass123!",
            "first_name": "Jane",
            "last_name": "Doe",
        })
        assert resp.status_code == 409

    async def test_register_invalid_email(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "TestPass123!",
            "first_name": "Jane",
            "last_name": "Doe",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client, student_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": student_user.email,
            "password": "TestPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["expires_in"] == 900

    async def test_login_wrong_password(self, client, student_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": student_user.email,
            "password": "WrongPass!",
        })
        assert resp.status_code == 401
```

### 6.2 Enrollment Concurrency Test

```python
# tests/integration/test_enrollment_concurrency.py
import asyncio

class TestEnrollmentConcurrency:
    async def test_capacity_enforced_under_concurrency(self, client, course_with_capacity_1):
        """Ensure only max_capacity enrollments succeed when many happen simultaneously."""
        course = course_with_capacity_1  # max_capacity = 1

        # Create 10 students
        students = [await create_test_student(client) for _ in range(10)]

        # All enroll simultaneously
        tasks = [
            client.post(
                "/api/v1/enrollments",
                json={"course_id": str(course.id)},
                headers=student.auth_headers,
            )
            for student in students
        ]
        responses = await asyncio.gather(*tasks)

        success = [r for r in responses if r.status_code == 201]
        rejected = [r for r in responses if r.status_code == 409]

        assert len(success) == 1  # Exactly one succeeds
        assert len(rejected) == 9  # Rest are rejected

    async def test_idempotent_enrollment(self, client, auth_headers, ready_course):
        """Same student enrolling twice gets same result."""
        resp1 = await client.post(
            "/api/v1/enrollments",
            json={"course_id": str(ready_course.id), "idempotency_key": "test-idem-1"},
            headers=auth_headers,
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/enrollments",
            json={"course_id": str(ready_course.id), "idempotency_key": "test-idem-1"},
            headers=auth_headers,
        )
        # Returns existing enrollment
        assert resp2.json()["data"]["id"] == resp1.json()["data"]["id"]
```

## 7. AI-Specific Tests

### 7.1 RAG Pipeline Tests

```python
# tests/integration/test_ai_qa.py

class TestAIQA:
    async def test_ask_question_returns_cited_answer(self, client, enrolled_student_headers, ready_course_with_content):
        resp = await client.post("/api/v1/ai/ask", json={
            "course_id": str(ready_course_with_content.id),
            "question": "What is machine learning?",
        }, headers=enrolled_student_headers)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["answer"]  # Non-empty
        assert len(data["citations"]) > 0
        assert all("chunk_id" in c for c in data["citations"])
        assert data["confidence"] in ("high", "medium", "low")

    async def test_ask_irrelevant_question_refuses(self, client, enrolled_student_headers, ready_course_with_content):
        resp = await client.post("/api/v1/ai/ask", json={
            "course_id": str(ready_course_with_content.id),
            "question": "What is the population of Mars?",
        }, headers=enrolled_student_headers)

        data = resp.json()["data"]
        # Should refuse or indicate low confidence
        assert data["confidence"] == "low" or "not enough information" in data["answer"].lower()

    async def test_ask_without_enrollment_forbidden(self, client, student_headers, ready_course):
        resp = await client.post("/api/v1/ai/ask", json={
            "course_id": str(ready_course.id),
            "question": "What is ML?",
        }, headers=student_headers)
        assert resp.status_code == 403
```

### 7.2 LLM Mock for Testing

```python
# tests/conftest.py
import respx

@pytest.fixture
def mock_llm():
    """Mock LLM API responses for testing."""
    with respx.mock:
        # Mock chat completion
        respx.post(f"{settings.LLM_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{
                    "message": {
                        "content": "Based on the course materials [1], machine learning is..."
                    }
                }],
                "usage": {"prompt_tokens": 500, "completion_tokens": 100}
            })
        )

        # Mock embeddings
        respx.post(f"{settings.EMBEDDING_BASE_URL}/embeddings").mock(
            return_value=httpx.Response(200, json={
                "data": [{"embedding": [0.1] * 1536}]
            })
        )

        yield
```

## 8. Load Testing (Locust)

### 8.1 Enrollment Load Test

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class EduCorpUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:80"

    def on_start(self):
        """Login and get token."""
        resp = self.client.post("/api/v1/auth/login", json={
            "email": f"loadtest-{self.greenlet.getcurrent().minimal_ident}@test.com",
            "password": "TestPass123!",
        })
        self.token = resp.json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def browse_catalog(self):
        self.client.get("/api/v1/courses?page=1&page_size=20", headers=self.headers)

    @task(2)
    def view_course(self):
        self.client.get(f"/api/v1/courses/{SAMPLE_COURSE_ID}", headers=self.headers)

    @task(1)
    def enroll(self):
        self.client.post("/api/v1/enrollments", json={
            "course_id": SAMPLE_COURSE_ID,
        }, headers=self.headers)

    @task(2)
    def ai_ask(self):
        self.client.post("/api/v1/ai/ask", json={
            "course_id": SAMPLE_COURSE_ID,
            "question": "What are the main topics?",
        }, headers=self.headers)
```

## 9. Testing Per Phase

| Phase | Test Focus | Test Types |
|-------|-----------|-----------|
| **Phase 0** | Infrastructure health. Can services start? Can they connect to DBs? | Health check smoke tests |
| **Phase 1** | Auth flows: register, login, JWT, RBAC, password reset | Unit + integration |
| **Phase 2** | Course CRUD, module management, asset upload, validation | Unit + integration |
| **Phase 3** | Publishing workflow, chunking, embedding, search | Integration + mock LLM |
| **Phase 4** | Enrollment (idempotency, capacity, prerequisites), progress, completion | Integration + concurrency |
| **Phase 5** | AI Q&A (retrieval, citation, streaming, refusal), instructor tools | Integration + mock LLM |
| **Phase 6** | Notification delivery, analytics aggregation, event consumption | Integration + Kafka |
| **Phase 7** | End-to-end journeys, load testing, security scan | E2E + load + security |

## 10. CI Test Configuration

```yaml
# pytest.ini / pyproject.toml section
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: Unit tests (fast, no external deps)",
    "integration: Integration tests (require DB/Redis)",
    "e2e: End-to-end tests (require full stack)",
    "slow: Tests that take >10s",
    "load: Load/stress tests",
]
filterwarnings = ["ignore::DeprecationWarning"]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*", "alembic/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

Running tests:
```bash
# Unit tests only (fast)
pytest -m unit -v

# Integration tests
pytest -m integration -v

# All tests with coverage
pytest --cov=app --cov-report=html -v

# Specific service
cd services/auth && pytest tests/ -v
```
