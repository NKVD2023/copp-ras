from app import create_app
from flask import url_for

app = create_app()
app.config['TESTING'] = True
with app.test_client() as client:
    with app.app_context():
        from app.models import User
        admin = User.query.filter_by(username='admin').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
    
    resp = client.get('/admin/')
    print("Dashboard status:", resp.status_code)
    
    resp_reports = client.get('/admin/reports')
    print("Reports status:", resp_reports.status_code)
