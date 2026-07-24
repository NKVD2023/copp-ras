from app import create_app, db
from app.models import User
app = create_app()
app.testing = True
client = app.test_client()

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        print("No admin user found. Creating one...")
        admin = User(username='admin_test', role='admin')
        admin.set_password('admin_test')
        db.session.add(admin)
        db.session.commit()
    admin_id = admin.id

with client.session_transaction() as sess:
    sess['_user_id'] = str(admin_id)
    sess['_fresh'] = True

routes_to_test = [
    '/admin/',
    '/admin/users',
    '/admin/templates',
    '/admin/files',
    '/'
]

for route in routes_to_test:
    response = client.get(route, follow_redirects=True)
    print(f"{route}: {response.status_code}")
    if response.status_code == 500:
        print(f"Error on {route}:\n{response.data.decode('utf-8')}")

