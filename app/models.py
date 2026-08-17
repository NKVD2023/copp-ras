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

# Таблица связи "Многие-ко-Многим" для файлов, прикрепленных к шаблонам
report_attachments = db.Table('report_attachments',
    db.Column('template_id', db.Integer, db.ForeignKey('report_templates.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('uploaded_files.id'), primary_key=True)
)

class UploadedFile(db.Model):
    """
    Модель загруженного файла (письмо, инструкция).
    """
    __tablename__ = 'uploaded_files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256))          # Оригинальное имя файла
    filepath = db.Column(db.String(256))          # Внутренний путь на сервере (со случайным именем)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id')) # Кто загрузил
    file_size = db.Column(db.Integer)             # Размер в байтах

    uploader = db.relationship('User', backref='uploaded_files')

class User(UserMixin, db.Model):
    """
    Модель пользователя системы.
    Поддерживает авторизацию (UserMixin).
    Роли (role): 'admin' (администратор), 'user' (обычный пользователь), 'manager' (наблюдатель).
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
    period_data = db.Column(JSON, nullable=True) # Строгие структурированные данные о периоде
    deadline = db.Column(db.Date)             # Дедлайн сдачи
    is_published = db.Column(db.Boolean, default=False)  # Виден ли пользователям
    is_completed = db.Column(db.Boolean, default=False)  # Завершен ли сбор (вручную)
    is_archived = db.Column(db.Boolean, default=False)   # Перенесен ли в архив
    is_template = db.Column(db.Boolean, default=False)   # Является ли это чистым шаблоном (без дедлайна)
    schema = db.Column(JSON)                  # Структура: листы, столбцы, типы полей
    
    # Отношение: какие файлы прикреплены к отчету
    attachments = db.relationship('UploadedFile', secondary=report_attachments, backref=db.backref('reports', lazy='dynamic'))

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
    ip_address = db.Column(db.String(45))     # IP-адрес клиента
    
    user = db.relationship('User', backref='action_logs')

@login_manager.user_loader
def load_user(id: str) -> User:
    """Загрузчик пользователя для Flask-Login на основе ID сессии."""
    return User.query.get(int(id))

class BackgroundTask(db.Model):
    """
    Модель для отслеживания фоновых задач (например, генерация больших Excel файлов).
    Используется для поллинга статуса из браузера, заменяя Celery.
    """
    __tablename__ = 'background_tasks'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    status = db.Column(db.String(20), default='PENDING') # PENDING, SUCCESS, FAILED
    result_path = db.Column(db.String(256), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

class Dictionary(db.Model):
    """
    Модель для хранения справочников (выпадающих списков).
    """
    __tablename__ = 'dictionaries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    items = db.Column(JSON, nullable=False, default=list) # Список строк (вариантов ответа)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReportDraft(db.Model):
    """
    Модель облачного черновика отчёта.
    Хранит временные данные пользователя до финальной сдачи.
    Один черновик на пару (пользователь, шаблон).
    Автоматически удаляется при успешной сдаче отчёта.
    """
    __tablename__ = 'report_drafts'
    id          = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data        = db.Column(JSON)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('template_id', 'user_id', name='uq_draft_template_user'),)

    template = db.relationship('ReportTemplate', backref='drafts')
    user     = db.relationship('User', backref='drafts')