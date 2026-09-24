import os
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Department

from config import config_map

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # Use the testing config from config_map
    app = create_app(config_map['testing'])
    
    # Establish an application context before running the tests.
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def init_database(app):
    """Create a default admin user and a standard user for tests."""
    with app.app_context():
        # Clear database to ensure clean state per test
        db.drop_all()
        db.create_all()

        admin = User(username='testadmin', role='admin')
        admin.set_password('admin123')
        
        user = User(username='testuser', role='user')
        user.set_password('user123')
        
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()
        
        yield db

        db.session.remove()
        db.drop_all()
