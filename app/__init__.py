"""
Основной модуль инициализации Flask-приложения (Core).
Здесь создаются экземпляры расширений (SQLAlchemy, LoginManager, CSRFProtect),
а также находится фабрика приложения `create_app`, которая собирает все блюпринты.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

# Инициализация глобальных расширений Flask
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Авторизуйтесь для доступа к платформе."
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_class: type = Config) -> Flask:
    """
    Фабрика создания Flask-приложения.
    Инициализирует настройки, подключает базу данных, менеджер авторизации, CSRF-защиту
    и регистрирует все маршруты (блюпринты) системы.

    :param config_class: Класс с настройками конфигурации (по умолчанию config.Config).
    :return: Инициализированный объект Flask-приложения.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Привязываем расширения к текущему приложению
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def add_security_headers(response):
        """
        Добавляет заголовки безопасности HTTP к каждому ответу.
        Защищает от Clickjacking и MIME-sniffing.
        """
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data:; "
            "object-src 'none';"
        )
        return response

    @app.context_processor
    def inject_config() -> dict:
        """
        Добавляет объект конфигурации во все шаблоны Jinja2.
        Позволяет обращаться к настройкам напрямую из HTML-кода (например, {{ config.APP_NAME }}).
        """
        return dict(config=app.config)

    from datetime import timedelta

    @app.template_filter('msk_time')
    def msk_time_filter(dt):
        """
        Jinja фильтр: Сдвигает время из базы данных (UTC) на Московское (UTC+3) 
        для корректного отображения в интерфейсе.
        Использование в шаблоне: {{ dt_obj | msk_time }}
        """
        if dt:
            return dt + timedelta(hours=3)
        return dt

    # Импортируем блюпринты локально, чтобы избежать циклических импортов
    from app.auth.routes import auth_bp
    from app.admin import admin_bp
    from app.reports import reports_bp

    # Регистрация маршрутов
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/')

    return app