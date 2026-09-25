"""app/models/announcement.py — Модель объявлений для пользователей."""
from app.extensions import db
from datetime import datetime
from sqlalchemy import JSON


class Announcement(db.Model):
    """
    Объявление от администратора для учреждений/пользователей.
    Отображается над календарем в личном кабинете.
    """
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # Тип важности: info (синий/нейтральный), warning (янтарный), danger (розово-красный), success (зеленый)
    type = db.Column(db.String(32), default='info')
    is_active = db.Column(db.Boolean, default=True)

    # Таргетирование:
    # 'all' — всем
    # 'specific' — только выбранным отделам и/или группам
    target_type = db.Column(db.String(20), default='all')
    target_departments = db.Column(JSON, default=list)  # список int dept_id
    target_groups = db.Column(JSON, default=list)       # список str наименований групп (['СПО', 'ВУЗ'])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    author = db.relationship('User', backref=db.backref('announcements', lazy='dynamic'))

    def is_visible_to_user(self, user) -> bool:
        """Проверяет, видно ли объявление конкретному пользователю."""
        if not self.is_active:
            return False
        if not user or not user.is_authenticated:
            return False
        if user.role in ['admin', 'manager']:
            return True
        if self.target_type == 'all':
            return True

        depts = self.target_departments or []
        groups = self.target_groups or []

        dept_match = bool(depts and user.department_id in depts)
        group_match = bool(groups and user.group in groups)

        if depts and groups:
            return dept_match or group_match
        if depts:
            return dept_match
        if groups:
            return group_match

        return True

    def __repr__(self):
        return f'<Announcement {self.id}: {self.title}>'
