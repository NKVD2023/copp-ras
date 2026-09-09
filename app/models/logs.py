"""app/models/logs.py — Журнал действий пользователей (аудит)."""
from app.extensions import db
from datetime import datetime

class ActionLog(db.Model):
    __tablename__ = 'action_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(128))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user = db.relationship('User', backref='action_logs')
