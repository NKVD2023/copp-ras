"""
Модуль моделей базы данных (Database Models).
Описывает структуру всех таблиц в SQLite с использованием SQLAlchemy ORM.
"""
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import JSON
from datetime import date, datetime

# Таблица связи "Многие-ко-Многим" для прав доступа пользователей к конкретным шаблонам
user_template_access = db.Table('user_template_access',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('template_id', db.Integer, db.ForeignKey('report_templates.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """
    Модель пользователя системы.
    Поддерживает авторизацию (UserMixin).
    Роли (role): 'admin' (администратор), 'user' (обычный пользователь), 'viewer' (наблюдатель).
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    description = db.Column(db.String(256))  # Например, название муниципалитета или организации
    role = db.Column(db.String(20), default='user')
    group = db.Column(db.String(50), nullable=True) # Группа: СПО, ВУЗ, Школы, Работодатели
    
    # Отношение: к каким шаблонам пользователь имеет доступ для заполнения
    assigned_templates = db.relationship('ReportTemplate', secondary=user_template_access, backref=db.backref('assigned_users', lazy='dynamic'))

    def set_password(self, password: str):
        """Хеширует и устанавливает новый пароль пользователя."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Проверяет соответствие введенного пароля сохраненному хешу."""
        return check_password_hash(self.password_hash, password)

class ReportTemplate(db.Model):
    """
    Модель шаблона отчета (конструктора).
    Хранит структуру отчета в поле `schema` в формате JSON.
    """
    __tablename__ = 'report_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))          # Полное название шаблона
    short_name = db.Column(db.String(64))     # Короткое имя для удобства
    period = db.Column(db.String(128))        # Период сдачи (например, "I квартал 2026")
    deadline = db.Column(db.Date)             # Дедлайн сдачи
    is_published = db.Column(db.Boolean, default=False)  # Виден ли пользователям
    is_archived = db.Column(db.Boolean, default=False)   # Перенесен ли в архив
    is_template = db.Column(db.Boolean, default=False)   # Является ли это чистым шаблоном (без дедлайна)
    schema = db.Column(JSON)                  # Структура: листы, столбцы, типы полей

class ReportSubmission(db.Model):
    """
    Модель заполненного отчета (Submission).
    Связывает конкретного пользователя и шаблон, данные хранятся в `data` как JSON.
    """
    __tablename__ = 'report_submissions'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data = db.Column(JSON)                    # Введенные пользователем значения полей
    
    # Связи для удобной навигации
    template = db.relationship('ReportTemplate', backref='submissions')
    user = db.relationship('User', backref='submissions')

class ActionLog(db.Model):
    """
    Модель записи журнала действий (Логов).
    Используется для аудита действий пользователей и администраторов (кто, что и когда сделал).
    """
    __tablename__ = 'action_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(128))        # Тип действия (например, 'Вход', 'Удаление пользователя')
    details = db.Column(db.Text)              # Дополнительная информация
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='action_logs')

@login_manager.user_loader
def load_user(id: str) -> User:
    """Загрузчик пользователя для Flask-Login на основе ID сессии."""
    return User.query.get(int(id))