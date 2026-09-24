import pytest
from app.models import User

def test_login_page_loads(client):
    """Test that the login page loads correctly."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'name="username"' in response.data
    assert b'name="password"' in response.data

def test_successful_login(client, init_database):
    """Test that a user can login with correct credentials."""
    response = client.post(
        '/auth/login',
        data={'username': 'testuser', 'password': 'user123'},
        follow_redirects=True
    )
    assert response.status_code == 200
    # Assuming successful login redirects to dashboard or reports
    assert b'testuser' in response.data

def test_failed_login(client, init_database):
    """Test that a user cannot login with incorrect credentials."""
    response = client.post(
        '/auth/login',
        data={'username': 'testuser', 'password': 'wrongpassword'},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'testuser' not in response.data or b'error' in response.data.lower() or b'alert' in response.data.lower()

def test_admin_access(client, init_database):
    """Test that admin can access admin panel but user cannot."""
    # Login as user
    client.post('/auth/login', data={'username': 'testuser', 'password': 'user123'}, follow_redirects=True)
    response = client.get('/admin/', follow_redirects=True)
    # Should be redirected or get 403 Forbidden
    assert b'testadmin' not in response.data

    # Login as admin
    client.get('/auth/logout')
    client.post('/auth/login', data={'username': 'testadmin', 'password': 'admin123'}, follow_redirects=True)
    response = client.get('/admin/', follow_redirects=True)
    assert response.status_code == 200
