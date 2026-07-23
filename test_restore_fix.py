import os
import shutil
import sqlite3
from app import create_app, db
from app.models import User, ActionLog
from flask_login import current_user, login_user

if os.path.exists('test.db'):
    os.remove('test.db')

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

with app.test_request_context():
    db.create_all()
    u = User(username='admin', password_hash='123', role='admin')
    db.session.add(u)
    db.session.commit()
    print("Initial users:", User.query.count())

    shutil.copy2('test.db', 'test_backup.db')
    print("Backup created.")

    u = User.query.first()
    db.session.delete(u)
    db.session.commit()
    print("Users after delete:", User.query.count())

with app.test_request_context():
    u = User.query.first() # None, because it was deleted
    # But let's say we are logged in from session cookie
    u_admin = User(id=1, username='admin', role='admin')
    login_user(u_admin) # Bypass actual db lookup for login_user just to simulate current_user
    
    # 1. Close session
    db.session.remove()
    # 2. Dispose engine
    db.engine.dispose()
    
    # 3. Restore
    shutil.copy2('test_backup.db', 'test.db')
    
    # 4. Log action (will create a new session)
    log = ActionLog(user_id=current_user.id, action='Restore', details='Restored')
    db.session.add(log)
    db.session.commit()
    print("Restore logged.")

with app.app_context():
    print("Final users:", User.query.count())
    print("Final logs:", ActionLog.query.count())

