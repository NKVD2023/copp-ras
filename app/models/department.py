"""app/models/department.py — Модель отдела (Department).

Отдел объединяет:
  - одного руководителя (manager_id → User)
  - список пользователей (backref через User.department_id)
  - список шаблонов отчётов (M2M через department_templates)

Один пользователь принадлежит ровно одному отделу (nullable=True для
обратной совместимости с уже существующими пользователями).
"""
from app.extensions import db

# Вспомогательная таблица M2M: отдел ↔ шаблоны отчётов
department_templates = db.Table(
    'department_templates',
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
    db.Column('template_id',   db.Integer, db.ForeignKey('report_templates.id', ondelete='CASCADE'), primary_key=True),
)


class Department(db.Model):
    """Отдел — организационная единица с руководителем и набором пользователей."""
    __tablename__ = 'departments'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(128), nullable=False, unique=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Руководитель отдела (User с ролью manager)
    manager = db.relationship(
        'User',
        foreign_keys=[manager_id],
        backref=db.backref('managed_department', uselist=False),
    )

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

    def __repr__(self) -> str:
        return f'<Department {self.id}: {self.name}>'
