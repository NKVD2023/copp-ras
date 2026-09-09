import os
from app import create_app
from app.extensions import db
from app.models import User
from config import config_map

# Выбор конфигурации через переменную окружения FLASK_CONFIG
# По умолчанию — DevelopmentConfig (локальная разработка)
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_map.get(config_name, config_map['default']))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("=== Система готова. Учётная запись администратора: admin / admin123 ===")

    app.run(debug=True, host='0.0.0.0', port=5001)
