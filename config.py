import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-copp'
    
    # Путь к файлу базы данных SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'reports.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ПЕРЕКЛЮЧАТЕЛЬ ИНФОГРАФИКИ
    ENABLE_CHARTS = True