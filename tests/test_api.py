import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root_redirect(client: AsyncClient):
    response = await client.get("/")
    # Should redirect to /login or /dashboard depending on session, 
    # but since we have no session, it should redirect to /login
    # Redirect response code is 307 (Temporary Redirect) or 302 (Found)
    # FastAPI RedirectResponse default is 307.
    # But wait, RedirectResponse default is 307.
    # Let's check if it follows redirects or not. httpx follows redirects by default? No.
    assert response.status_code in [302, 307]
    assert response.headers["location"] == "/login"

@pytest.mark.asyncio
async def test_login_page(client: AsyncClient):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Login" in response.text or "login" in response.text

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    # Assuming we might add a health check endpoint later, but for now let's test a known 404
    response = await client.get("/non-existent")
    assert response.status_code in [404, 401]

@pytest.mark.asyncio
async def test_personas_page(client: AsyncClient):
    from unittest.mock import patch, AsyncMock, MagicMock
    from core.security import get_current_user
    import uuid
    
    mock_user_data = {"id": "123456789", "first_name": "Test"}
    mock_db_user = MagicMock()
    mock_db_user.id = uuid.uuid4()
    
    # Mock get_current_user to return logged in user
    # We need to override the dependency or patch the function used in the router.
    # api/web_router.py imports get_current_user from core.security.
    # Since it's a function call inside the route handler (not a Depends), we patch it.
    
    with patch("api.web_router.get_current_user", return_value=mock_user_data), \
         patch("repository.user_repository.get_user_by_telegram_id", new_callable=AsyncMock) as mock_get_user, \
         patch("repository.persona_repository.get_user_personas", new_callable=AsyncMock) as mock_get_personas, \
         patch("core.database.get_async_session") as mock_get_session:
         
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_get_user.return_value = mock_db_user
        mock_get_personas.return_value = []
        
        response = await client.get("/personas")
        assert response.status_code == 200
        assert "My Personas" in response.text

@pytest.mark.asyncio
async def test_admin_dashboard(client: AsyncClient):
    from unittest.mock import patch, AsyncMock
    
    mock_user_data = {"id": "123456789", "first_name": "Admin"}
    mock_stats = {
        "total_users": 10,
        "total_conversations": 100,
        "total_personas": 5,
        "active_users": 3
    }
    
    with patch("api.web_router.get_current_user", return_value=mock_user_data), \
         patch("api.web_router.settings") as mock_settings, \
         patch("repository.stats_repository.get_system_stats", new_callable=AsyncMock) as mock_get_stats:
         
        mock_settings.admin_ids = [123456789]
         
        mock_get_stats.return_value = mock_stats
        
        response = await client.get("/admin")
        assert response.status_code == 200
        assert "Admin Dashboard" in response.text
        assert "10" in response.text # total users

@pytest.mark.asyncio
async def test_admin_access_denied(client: AsyncClient):
    from unittest.mock import patch
    
    mock_user_data = {"id": "987654321", "first_name": "User"}
    
    with patch("api.web_router.get_current_user", return_value=mock_user_data), \
         patch("api.web_router.settings") as mock_settings:
        
        mock_settings.admin_ids = [123456789]
         
        response = await client.get("/admin")
        assert response.status_code == 403
