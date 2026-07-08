from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("=== Система готова. Учетная запись администратора: admin / admin123 ===")
            
    app.run(debug=True, host='0.0.0.0', port=5000)