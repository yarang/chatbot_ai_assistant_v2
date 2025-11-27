import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
from main import app

@pytest.mark.asyncio
async def test_index_redirect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 307  # Temporary Redirect to /login or /dashboard (if logged in)
    assert "/login" in response.headers["location"]

@pytest.mark.asyncio
async def test_login_page():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_telegram_auth_callback_success():
    with patch("api.web_router.check_telegram_authorization", return_value=True), \
         patch("api.web_router.create_session_token", return_value="mock_token"), \
         patch("api.web_router.settings") as mock_settings:
        
        mock_settings.admin_ids = [12345]
        mock_settings.telegram.bot_token = "test_token"
        
        params = {
            "id": "12345",
            "first_name": "Test",
            "username": "testuser",
            "photo_url": "http://example.com/photo.jpg",
            "auth_date": "1234567890",
            "hash": "mock_hash"
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/telegram/callback", params=params)
            
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]
        assert "session=mock_token" in response.headers["set-cookie"]

@pytest.mark.asyncio
async def test_dashboard_access_denied_without_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/dashboard")
    assert response.status_code == 307
    assert "/login" in response.headers["location"]

@pytest.mark.asyncio
async def test_dashboard_access_success():
    with patch("api.web_router.get_current_user", return_value={"id": "12345", "first_name": "Test"}), \
         patch("api.web_router.get_chat_room_by_telegram_id", new_callable=AsyncMock) as mock_get_room, \
         patch("api.web_router.get_history", new_callable=AsyncMock) as mock_get_history:
         
        mock_get_room.return_value = MagicMock(id="room_id")
        mock_get_history.return_value = []
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/dashboard")
            
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
