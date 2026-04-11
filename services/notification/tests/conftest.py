from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def api_client(app):
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
