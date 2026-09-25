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

    # ── Проверка срока жизни сессии (24 часа) ──────────────────────────────────
    @app.before_request
    def enforce_session_lifetime():
        from flask import request, session, redirect, url_for, jsonify
        from flask_login import current_user, logout_user
        import time

        # Статические файлы, вход и выход пропускаем
        if request.endpoint == 'static' or (request.path and request.path.startswith('/static/')):
            return
        if request.endpoint in ['auth.login', 'auth.logout'] or (request.path and request.path.startswith('/auth/')):
            return

        if current_user.is_authenticated:
            login_time = session.get('login_time')
            # 24 часа = 86400 секунд
            if not login_time or (time.time() - float(login_time) > 86400):
                logout_user()
                session.clear()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    return jsonify({
                        'status': 'session_expired',
                        'message': 'Срок сессии истек',
                        'redirect': url_for('auth.login')
                    }), 401
                return redirect(url_for('auth.login'))

    # ── Обработка неавторизованного доступа (AJAX / обычный) ───────────────────
    @login_manager.unauthorized_handler
    def handle_unauthorized():
        from flask import request, redirect, url_for, jsonify
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'status': 'unauthorized',
                'message': 'Требуется авторизация',
                'redirect': url_for('auth.login')
            }), 401
        return redirect(url_for('auth.login'))

    # ── Режим технических работ ────────────────────────────────────────────────
    @app.before_request
    def check_maintenance():
        from flask import request, render_template, jsonify
        from flask_login import current_user
        from app.services.maintenance import get_maintenance_status

        # Статические файлы всегда доступны
        if request.endpoint == 'static' or (request.path and request.path.startswith('/static/')):
            return

        # Авторизованный администратор имеет полный доступ
        if current_user.is_authenticated and current_user.role == 'admin':
            return

        # Вход и выход разрешены (чтобы админ мог войти в систему)
        if request.endpoint in ['auth.login', 'auth.logout'] or (request.path and request.path.startswith('/auth/')):
            return

        # Проверка активности техработ
        status = get_maintenance_status()
        if status.get('in_maintenance'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'status': 'maintenance',
                    'message': status.get('message')
                }), 503
            return render_template('maintenance.html', maintenance=status), 503

    # ── Security & Cache headers ──────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        """Добавляет заголовки безопасности HTTP и запрет кеширования динамического HTML."""
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
        # Запрет кеширования HTML-страниц (защита от устаревшего DOM и скриптов в браузере)
        if response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # ── Jinja2 Context Processors ─────────────────────────────────────────────
    @app.context_processor
    def inject_global_data() -> dict:
        """Прокидывает конфиг и статус техработ в каждый шаблон."""
        from app.services.maintenance import get_maintenance_status
        return dict(
            config=app.config,
            maintenance_status=get_maintenance_status()
        )

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