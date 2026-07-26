from app import create_app, db
from app.models import User

def upgrade_viewer_to_manager():
    app = create_app()
    with app.app_context():
        viewers = User.query.filter_by(role='manager').all()
        count = 0
        for viewer in viewers:
            viewer.role = 'manager'
            count += 1
        
        if count > 0:
            db.session.commit()
            print(f"Успешно обновлено ролей: {count} (viewer -> manager)")
        else:
            print("Пользователи с ролью viewer не найдены.")

if __name__ == '__main__':
    upgrade_viewer_to_manager()
