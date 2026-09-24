import pytest
from app.models import User, Department
from app.extensions import db

def test_create_user(init_database):
    """Test creating a new user in the database."""
    user = User(username='new_user', role='user')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    retrieved_user = User.query.filter_by(username='new_user').first()
    assert retrieved_user is not None
    assert retrieved_user.username == 'new_user'
    assert retrieved_user.role == 'user'
    assert retrieved_user.check_password('password123') is True
    assert retrieved_user.check_password('wrongpassword') is False

def test_department_relationship(init_database):
    """Test the relationship between users and departments."""
    dept = Department(name='Test Department')
    db.session.add(dept)
    db.session.commit()

    user = User.query.filter_by(username='testuser').first()
    user.department_id = dept.id
    db.session.commit()

    assert user.department.name == 'Test Department'
    assert user in dept.members.all()
