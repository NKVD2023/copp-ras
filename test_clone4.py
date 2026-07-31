import json
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
        'new_short_name': 'test_short',
        'new_name': 'test_full',
        'new_period': '',
        'new_period_data': '{',
        'new_deadline': '2026-08-01',
        'action': 'publish',
        'attached_files': []
    }
    
    app.config['WTF_CSRF_ENABLED'] = False
    
    resp = client.post(f'/admin/clone_template/{template.id}', data=data)
    print("Status:", resp.status_code)
    if resp.status_code == 500:
        print("ERROR RECEIVED 500!")
    
