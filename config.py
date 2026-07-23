import os
import logging

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        secret_file = os.path.join(basedir, '.secret_key')
        try:
            with open(secret_file, 'r') as f:
                SECRET_KEY = f.read().strip()
        except FileNotFoundError:
            SECRET_KEY = os.urandom(24).hex()
            try:
                with open(secret_file, 'w') as f:
                    f.write(SECRET_KEY)
            except IOError:
                pass
            logging.warning("SECRET_KEY not set in env. Generated and saved to .secret_key")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'reports.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # БЕЗОПАСНОСТЬ COOKIES (Session Security)
    SESSION_COOKIE_SECURE = True              # Куки только по HTTPS (отключить при локальном запуске)
    SESSION_COOKIE_HTTPONLY = True            # Запрет доступа к куки из JavaScript (XSS защита)
    SESSION_COOKIE_SAMESITE = 'Lax'          # Защита от CSRF
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # ПЕРЕКЛЮЧАТЕЛЬ ИНФОГРАФИКИ
    ENABLE_CHARTS = True