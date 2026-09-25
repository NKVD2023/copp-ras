import os
from datetime import timedelta
import logging

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Базовая конфигурация. Общие настройки для всех окружений."""

    # ── Secret Key ──────────────────────────────────────────────────────────
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

    # ── Database ─────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or 'sqlite:///' + os.path.join(basedir, 'reports.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Session & Cookie Security ─────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_REFRESH_EACH_REQUEST = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True

    # ── Features ──────────────────────────────────────────────────────────────
    ENABLE_CHARTS = True


class DevelopmentConfig(Config):
    """
    Конфигурация для локальной разработки.
    Отключает HTTPS-куки, включает debug-режим Flask.

    Использование:
        FLASK_CONFIG=development python run.py
    """
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    # Отдельная БД для разработки (не трогает продакшн)
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL')
        or 'sqlite:///' + os.path.join(basedir, 'reports.db')
    )


class ProductionConfig(Config):
    """
    Конфигурация для продакшн-сервера.
    Все настройки безопасности включены.

    Использование:
        FLASK_CONFIG=production gunicorn wsgi:app
    """
    DEBUG = False


class TestingConfig(Config):
    """
    Конфигурация для автотестов.
    Использует in-memory SQLite для скорости.

    Использование:
        pytest
    """
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Отключаем CSRF в тестах


# Словарь для выбора конфига через переменную окружения FLASK_CONFIG
config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
