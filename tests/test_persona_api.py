import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from main import app
from core.security import get_current_user_required
import uuid
from datetime import datetime

# Mock User
mock_user_data = {
    "id": "123456789",
    "first_name": "Test",
    "username": "testuser",
    "photo_url": "http://example.com/photo.jpg"
}

# Mock DB User
mock_db_user = MagicMock()
mock_db_user.id = uuid.uuid4()
mock_db_user.telegram_id = 123456789

# Mock Persona
mock_persona = MagicMock()
mock_persona.id = uuid.uuid4()
mock_persona.user_id = mock_db_user.id
mock_persona.name = "Test Persona"
mock_persona.content = "You are a test persona."
mock_persona.description = "Description"
mock_persona.is_public = False
mock_persona.created_at = datetime.now()
mock_persona.updated_at = datetime.now()

@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user_required] = lambda: mock_user_data
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_persona(override_auth):
    with patch("repository.user_repository.get_user_by_telegram_id", new_callable=AsyncMock) as mock_get_user, \
         patch("api.persona_router.create_persona", new_callable=AsyncMock) as mock_create, \
         patch("core.database.get_async_session") as mock_get_session:
        
        # Mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_get_user.return_value = mock_db_user
        mock_create.return_value = mock_persona
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/persona/", json={
                "name": "Test Persona",
                "content": "You are a test persona.",
                "description": "Description",
                "is_public": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Persona"
            assert data["id"] == str(mock_persona.id)

@pytest.mark.asyncio
async def test_get_my_personas(override_auth):
    with patch("repository.user_repository.get_user_by_telegram_id", new_callable=AsyncMock) as mock_get_user, \
         patch("api.persona_router.get_user_personas", new_callable=AsyncMock) as mock_get_personas, \
         patch("core.database.get_async_session") as mock_get_session:
        
        # Mock session context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_get_user.return_value = mock_db_user
        mock_get_personas.return_value = [mock_persona]
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/persona/user/me")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Test Persona"
