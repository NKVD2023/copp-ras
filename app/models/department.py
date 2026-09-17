"""app/models/department.py — Модель отдела (Department).

Отдел объединяет:
  - список руководителей (manager_ids → JSON-список User.id)
  - список пользователей (backref через User.department_id)
  - список шаблонов отчётов (M2M через department_templates)

Один пользователь принадлежит ровно одному отделу (nullable=True для
обратной совместимости с уже существующими пользователями).
"""
import json
from app.extensions import db

# Вспомогательная таблица M2M: отдел ↔ шаблоны отчётов
department_templates = db.Table(
    'department_templates',
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
    db.Column('template_id',   db.Integer, db.ForeignKey('report_templates.id', ondelete='CASCADE'), primary_key=True),
)


class Department(db.Model):
    """Отдел — организационная единица с руководителями и набором пользователей."""
    __tablename__ = 'departments'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False, unique=True)
    manager_ids = db.Column(db.Text, nullable=True, default='[]')

    # Пользователи отдела (через User.department_id)
    members = db.relationship(
        'User',
        foreign_keys='User.department_id',
        backref=db.backref('department', uselist=False),
        lazy='dynamic',
    )

    # Назначенные шаблоны отчётов
    templates = db.relationship(
        'ReportTemplate',
        secondary=department_templates,
        backref=db.backref('departments', lazy='dynamic'),
        lazy='dynamic',
    )

    @property
    def manager_ids_list(self) -> list:
        """Возвращает список ID руководителей (из JSON-строки)."""
        if not self.manager_ids:
            return []
        try:
            result = json.loads(self.manager_ids)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @manager_ids_list.setter
    def manager_ids_list(self, ids: list):
        """Сохраняет список ID руководителей в JSON-строку."""
        self.manager_ids = json.dumps([int(i) for i in ids if i])

    @property
    def managers(self):
        """Возвращает список объектов User — руководителей отдела."""
        from app.models.user import User
        ids = self.manager_ids_list
        if not ids:
            return []
        return User.query.filter(User.id.in_(ids)).all()

    def __repr__(self) -> str:
        return f'<Department {self.id}: {self.name}>'
