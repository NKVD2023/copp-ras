from app import create_app, db
from app.models import BackgroundTask

def upgrade():
    app = create_app()
    with app.app_context():
        # SQLite: Create the new table if it doesn't exist
        db.create_all()
        print("Таблица background_tasks успешно проверена/создана.")

if __name__ == '__main__':
    upgrade()
