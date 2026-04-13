from __future__ import annotations

import pytest

from app.services.slug_service import SlugService


class TestSlugify:
    """Test the internal _slugify method."""

    def test_basic_title(self):
        assert SlugService._slugify("Introduction to Machine Learning") == "introduction-to-machine-learning"

    def test_special_characters(self):
        assert SlugService._slugify("C++ Programming: A Guide!") == "c-programming-a-guide"

    def test_extra_whitespace(self):
        assert SlugService._slugify("  lots   of   spaces  ") == "lots-of-spaces"

    def test_unicode(self):
        assert SlugService._slugify("Café résumé") == "cafe-resume"

    def test_empty_string(self):
        assert SlugService._slugify("") == ""

    def test_hyphens_preserved(self):
        assert SlugService._slugify("end-to-end testing") == "end-to-end-testing"

    def test_numbers(self):
        assert SlugService._slugify("101 Python Tips") == "101-python-tips"


class TestSlugGeneration:
    """Test slug generation with collision resolution."""

    @pytest.fixture
    def mock_repo(self):
        class FakeRepo:
            def __init__(self):
                self.slugs: set[str] = set()

            async def slug_exists(self, slug: str, *, exclude_id=None) -> bool:
                return slug in self.slugs
        return FakeRepo()

    async def test_no_collision(self, mock_repo):
        svc = SlugService(mock_repo)
        slug = await svc.generate("Test Course")
        assert slug == "test-course"

    async def test_collision_adds_suffix(self, mock_repo):
        mock_repo.slugs.add("test-course")
        svc = SlugService(mock_repo)
        slug = await svc.generate("Test Course")
        assert slug == "test-course-2"

    async def test_multiple_collisions(self, mock_repo):
        mock_repo.slugs.update({"test-course", "test-course-2", "test-course-3"})
        svc = SlugService(mock_repo)
        slug = await svc.generate("Test Course")
        assert slug == "test-course-4"
