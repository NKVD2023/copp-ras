"""
Утилита: Наполнение базы данных аналитики фейковыми или тестовыми данными.
"""
import sys
import os
import json
import random
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, ReportTemplate, ReportSubmission

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='TEST').first()
    if not user:
        user = User(username='TEST', role='user', description='Тестовый пользователь для аналитики')
        user.set_password('Aa123456')
        db.session.add(user)
        db.session.commit()
    
    short_name = "Тестовый отчет (Демо аналитики)"
    
    schema = [
        {
            "sheet_title": "Основной",
            "fields": [
                {"name": "f1", "label": "Количество поступивших заявок", "type": "number", "required": True},
                {"name": "f2", "label": "Одобренные заявки", "type": "number", "required": True},
                {"name": "f3", "label": "Бюджет (тыс. руб)", "type": "number", "required": True},
                {"name": "f4", "label": "Комментарий", "type": "text", "required": False}
            ]
        }
    ]
    
    periods = [
        ("I квартал 2026", date(2026, 3, 31)),
        ("II квартал 2026", date(2026, 6, 30)),
        ("III квартал 2026", date(2026, 9, 30)),
        ("IV квартал 2026", date(2026, 12, 31)),
        ("I квартал 2027", date(2027, 3, 31))
    ]
    
    old_templates = ReportTemplate.query.filter_by(short_name=short_name).all()
    for t in old_templates:
        ReportSubmission.query.filter_by(template_id=t.id).delete()
        db.session.delete(t)
    db.session.commit()
    
    base_f1 = 100
    base_f2 = 70
    base_f3 = 1000
    
    for i, (period_name, deadline) in enumerate(periods):
        t = ReportTemplate(
            name=f"{short_name} за {period_name}",
            short_name=short_name,
            period=period_name,
            schema=json.dumps(schema),
            is_published=True,
            deadline=deadline
        )
        db.session.add(t)
        db.session.flush()
        
        t.assigned_users.append(user)
        
        trend = i * 20
        data = {
            "f1": base_f1 + trend + random.randint(-10, 10),
            "f2": base_f2 + trend + random.randint(-15, 15),
            "f3": base_f3 + (trend * 10) + random.randint(-100, 100),
            "f4": "Всё идет по плану"
        }
        
        sub = ReportSubmission(
            template_id=t.id,
            user_id=user.id,
            data=data
        )
        db.session.add(sub)
        
    db.session.commit()
    print("Демо данные для аналитики успешно созданы для пользователя TEST!")
