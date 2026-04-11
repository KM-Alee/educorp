---
applyTo: "services/*/app/models/**/*.py,services/*/app/repositories/**/*.py,services/*/alembic/**/*.py"
---

# Database Conventions

## SQLAlchemy Models

### Base Configuration
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, String
from uuid import UUID, uuid4
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

### Model Rules
- All primary keys are UUID v4: `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`
- Always set `__table_args__ = {"schema": "<service_name>"}`
- Include `TimestampMixin` on every model
- Index all foreign keys and frequently filtered columns
- Use `Mapped[type]` annotations — never use `Column()` directly
- String columns must have explicit length: `String(500)`

### Schema Ownership
Each service owns exactly one PostgreSQL schema:
- `auth` → auth-service
- `course` → course-service
- `enrollment` → enrollment-service
- `progress` → progress-service
- `publishing` → publishing-service
- `notification` → notification-service
- `analytics` → analytics-service

**Never** query across schema boundaries. Use events or HTTP calls.

## Repository Pattern
```python
class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> T | None:
        return await self._session.get(self._model, id)
```

- One repository per aggregate root
- Repositories accept `AsyncSession` via constructor
- Return domain objects, not raw rows
- Use `session.flush()` (not `commit()`) — let the request handler commit

## Alembic Migrations
- Autogenerate as starting point, then review and edit
- Descriptive message: `alembic revision -m "add courses table"`
- Always implement both `upgrade()` and `downgrade()`
- Set `include_schemas=True` and `target_metadata` in `env.py`
- Run with: `alembic upgrade head`
- Test downgrade: `alembic downgrade -1`
