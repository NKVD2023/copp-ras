import os
import logging

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24).hex()
        logging.warning("SECRET_KEY not set. Using a randomly generated one.")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'reports.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # БЕЗОПАСНОСТЬ COOKIES (Session Security)
    SESSION_COOKIE_SECURE = True       # Куки передаются только по HTTPS
    SESSION_COOKIE_HTTPONLY = True     # Запрет доступа к куки из JavaScript (XSS защита)
    SESSION_COOKIE_SAMESITE = 'Lax'    # Защита от CSRF
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # ПЕРЕКЛЮЧАТЕЛЬ ИНФОГРАФИКИ
    ENABLE_CHARTS = True