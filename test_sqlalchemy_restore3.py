import os
import shutil
shutil.copy2('copp_backup_20260722_113402.db', 'reports.db')

from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Checkout connection
    u = User.query.first()
    
    # Dispose engine
    db.engine.dispose()
    
    # Overwrite file with a valid database
    shutil.copy2('copp_backup_20260722_113402.db', 'reports.db')
    print("File overwritten successfully!")
    
    # Commit something
    u.username = 'admin2'
    try:
        db.session.commit()
        print("Commit successful!")
    except Exception as e:
        print("Commit failed:", e)
