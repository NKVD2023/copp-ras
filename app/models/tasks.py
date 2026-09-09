"""app/models/tasks.py — Фоновые задачи (вместо Celery)."""
from app.extensions import db
from datetime import datetime

class BackgroundTask(db.Model):
    __tablename__ = 'background_tasks'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    status = db.Column(db.String(20), default='PENDING')
    result_path = db.Column(db.String(256), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
