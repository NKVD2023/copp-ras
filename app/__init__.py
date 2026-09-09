"""
app/__init__.py
Фабрика Flask-приложения (Application Factory).

Здесь только:
  - создание экземпляра Flask
  - подключение расширений из app.extensions
  - регистрация блюпринтов
  - регистрация Jinja2-фильтров и security-хуков

Все экземпляры расширений (db, login_manager, ...) — в app/extensions.py
Все модели БД — в app/models/
"""
from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_class: type = Config) -> Flask:
    """
    Фабрика создания Flask-приложения.

    :param config_class: Класс с настройками конфигурации (по умолчанию config.Config).
    :return: Инициализированный объект Flask-приложения.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Расширения ────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # ── База данных ───────────────────────────────────────────────────────────
    with app.app_context():
        from app import models  # noqa: F401 — регистрирует модели в SQLAlchemy
        db.create_all()

    # ── Security headers ──────────────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        """Добавляет заголовки безопасности HTTP к каждому ответу."""
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "object-src 'none';"
        )
        return response

    # ── Jinja2 Context Processors ─────────────────────────────────────────────
    @app.context_processor
    def inject_config() -> dict:
        """Прокидывает объект конфигурации в каждый шаблон."""
        return dict(config=app.config)

    # ── Jinja2 Filters ────────────────────────────────────────────────────────
    from datetime import timedelta

    @app.template_filter('msk_time')
    def msk_time_filter(dt):
        """Сдвигает datetime из UTC в МСК (UTC+3)."""
        if dt:
            return dt + timedelta(hours=3)
        return dt

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.auth.routes import auth_bp
    from app.admin import admin_bp
    from app.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/')

    return app