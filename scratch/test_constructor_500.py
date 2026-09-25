import os
import sys
sys.path.insert(0, os.path.abspath("."))
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

with app.app_context():
    # Создаем руководителя
    u = User.query.filter_by(username="test_manager_none").first()
    if not u:
        u = User(username="test_manager_none", role="manager")
        u.set_password("123")
        u.department_id = None
        db.session.add(u)
        db.session.commit()

    with app.test_client() as client:
        # Авторизуемся
        res = client.post('/auth/login', data={'username': 'test_manager_none', 'password': '123'}, follow_redirects=True)
        print("Login status:", res.status_code)
        
        # Пробуем зайти в конструктор
        response = client.get('/admin/constructor')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 500:
            print("500 Error Reproducible!")
        elif response.status_code == 302:
            print(f"Redirected to: {response.headers.get('Location')}")
            res2 = client.get(response.headers.get('Location'), follow_redirects=True)
            print(f"Redirect Status: {res2.status_code}")
        else:
            print("No 500 error locally.")
