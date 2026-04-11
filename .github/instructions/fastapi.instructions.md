---
applyTo: "services/*/app/**/*.py"
---

# FastAPI Service Conventions

## App Factory
Every service uses the app factory pattern with `lifespan`:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

def create_app() -> FastAPI:
    app = FastAPI(title="Service Name", lifespan=lifespan)
    app.include_router(v1_router, prefix="/api/v1")
    register_exception_handlers(app)
    return app
```

## Imports
- Always use `from __future__ import annotations` at the top of every file
- Import order: stdlib → third-party → local (ruff handles this)

## Dependencies
- Use `Depends()` for all injected resources
- Define dependency providers in `dependencies.py`
- Chain dependencies: `get_service` depends on `get_repository` depends on `get_session`

## Response Envelope
All responses use the standard envelope:
```python
class SuccessResponse(BaseModel, Generic[T]):
    data: T
    meta: dict[str, Any] = {}

class ErrorResponse(BaseModel):
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = []
```

## Route Handlers
- Keep handlers thin — delegate to service layer
- Always type-annotate return values
- Use `status_code=` parameter on decorators
- Use `response_model=` for OpenAPI documentation

## Pydantic Schemas
- Use `model_config = ConfigDict(from_attributes=True)` for ORM conversion
- Separate `Create`, `Update`, `Out` schemas
- Validate at schema level, not in handlers

## Error Handling
- Raise `EduCorpError` subclasses from service layer
- Never catch generic `Exception` in handlers
- Exception handlers in app factory convert to `ErrorResponse`

## Async/Await
- Every I/O operation must be `async`
- Use `asyncio.gather()` for independent concurrent operations
- Never use synchronous DB calls

## Configuration
- All config via Pydantic `BaseSettings` in `config.py`
- Environment variables prefixed with service name: `AUTH_`, `COURSE_`, etc.
- Never hardcode URLs, credentials, or timeouts
