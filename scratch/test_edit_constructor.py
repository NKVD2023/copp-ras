import os
import sys
sys.path.insert(0, os.path.abspath("."))
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import User, Department, ReportTemplate

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

with app.app_context():
    # Создаем шаблон и отдел
    t = ReportTemplate.query.filter_by(name="Test Template 77").first()
    if not t:
        t = ReportTemplate(name="Test Template 77", short_name="T77", schema="[]", is_template=True)
        db.session.add(t)
        db.session.commit()

    d = Department.query.filter_by(name="Test Dept").first()
    if not d:
        d = Department(name="Test Dept")
        db.session.add(d)
        db.session.commit()

    u = User.query.filter_by(username="test_manager_edit").first()
    if not u:
        u = User(username="test_manager_edit", role="manager")
        u.set_password("123")
        u.department_id = d.id
        db.session.add(u)
        db.session.commit()
        d.manager_ids_list = [u.id]
        db.session.commit()

    with app.test_client() as client:
        res = client.post('/auth/login', data={'username': 'test_manager_edit', 'password': '123'}, follow_redirects=True)
        print("Login status:", res.status_code)
        
        response = client.get(f'/admin/edit_constructor/{t.id}')
        print(f"Status Code edit_constructor: {response.status_code}")
        if response.status_code == 500:
            print("500 Error Reproducible!")
        else:
            print("No 500 error locally.")
