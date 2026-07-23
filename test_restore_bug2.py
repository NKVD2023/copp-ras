import os
import shutil
import sqlite3
from app import create_app, db
from app.models import User, ActionLog

# Initialize a clean database
if os.path.exists('test.db'):
    os.remove('test.db')

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

with app.app_context():
    db.create_all()
    u = User(username='admin', password_hash='123', role='admin')
    db.session.add(u)
    db.session.commit()
    print("Initial users:", User.query.count())

    # Create backup
    shutil.copy2('test.db', 'test_backup.db')
    print("Backup created.")

    # Delete the user!
    u = User.query.first()
    db.session.delete(u)
    db.session.commit()
    print("Users after delete:", User.query.count())

    # Now RESTORE in a new request context to simulate the Restore request
    with app.app_context():
        # current_user is loaded (checks out connection)
        u_dummy = User.query.first()
        
        # Dispose engine
        db.engine.dispose()
        
        # Restore file
        shutil.copy2('test_backup.db', 'test.db')
        
        # Log action (uses the checked-out connection!)
        log = ActionLog(user_id=1, action='Restore', details='Restored')
        db.session.add(log)
        db.session.commit()
        print("Restore and log action committed.")

    # Check final state
    with app.app_context():
        print("Final users:", User.query.count())

