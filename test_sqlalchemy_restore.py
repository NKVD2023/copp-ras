import os
from app import create_app, db
from app.models import User
import shutil

app = create_app()
with app.app_context():
    # Checkout connection
    u = User.query.first()
    print("User read:", u.username)
    
    # Dispose engine
    db.engine.dispose()
    
    # Overwrite file
    with open('reports.db', 'wb') as f:
        f.write(b'SQLite format 3\000' + b'A'*100)
    print("File overwritten successfully!")
    
    # Commit something
    u.username = 'admin2'
    try:
        db.session.commit()
        print("Commit successful!")
    except Exception as e:
        print("Commit failed:", e)
