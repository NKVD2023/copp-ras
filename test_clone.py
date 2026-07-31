from app import create_app, db
from app.models import User, ReportTemplate
from flask import Flask, request

app = create_app()

with app.test_client() as client:
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        template = ReportTemplate.query.first()
        
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        
    data = {
        'csrf_token': 'dummy',
        'new_short_name': 'test',
        'new_name': 'test',
        'new_period': 'period_test',
        'new_period_data': 'null',
        'new_deadline': '2026-10-10',
        'action': 'draft',
        'attached_files': ['2', '3']
    }
    
    # Disable CSRF for testing
    app.config['WTF_CSRF_ENABLED'] = False
    
    resp = client.post(f'/admin/clone_template/{template.id}', data=data)
    print("Status:", resp.status_code)
    if resp.status_code == 500:
        print(resp.data.decode('utf-8'))
