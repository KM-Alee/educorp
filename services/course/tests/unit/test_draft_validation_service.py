from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.schemas.common import DraftValidationIssue
from app.services.draft_validation_service import DraftValidationService


class TestDraftValidation:
    """Test draft validation rules."""

    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    async def test_missing_course(self, mock_session):
        svc = DraftValidationService(mock_session)
        svc._courses = MagicMock()
        svc._courses.get_by_id = AsyncMock(return_value=None)
        svc._modules = MagicMock()

        issues = await svc.validate(uuid4())
        assert len(issues) == 1
        assert issues[0].field == "course"

    async def test_missing_required_fields(self, mock_session):
        course = MagicMock()
        course.title = ""
        course.description = ""
        course.category = None
        course.difficulty = None

        svc = DraftValidationService(mock_session)
        svc._courses = MagicMock()
        svc._courses.get_by_id = AsyncMock(return_value=course)
        svc._modules = MagicMock()
        svc._modules.count_for_course = AsyncMock(return_value=0)
        svc._modules.list_for_course = AsyncMock(return_value=[])

        course_id = uuid4()
        issues = await svc.validate(course_id)
        fields = {i.field for i in issues}
        assert "title" in fields
        assert "description" in fields
        assert "category" in fields
        assert "difficulty" in fields
        assert "modules" in fields

    async def test_valid_draft(self, mock_session):
        course = MagicMock()
        course.title = "Valid Course"
        course.description = "A valid description"
        course.category = "Computer Science"
        course.difficulty = "beginner"

        module = MagicMock()
        module.title = "Module 1"
        module.sort_order = 0

        svc = DraftValidationService(mock_session)
        svc._courses = MagicMock()
        svc._courses.get_by_id = AsyncMock(return_value=course)
        svc._modules = MagicMock()
        svc._modules.count_for_course = AsyncMock(return_value=1)
        svc._modules.list_for_course = AsyncMock(return_value=[module])

        issues = await svc.validate(uuid4())
        assert len(issues) == 0
