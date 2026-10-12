import os
from app import create_app
from config import config_map

# Выбор конфигурации через переменную окружения FLASK_CONFIG (по умолчанию production для WSGI)
config_name = os.environ.get('FLASK_CONFIG', 'production')
app = create_app(config_map.get(config_name, config_map['default']))

if __name__ == '__main__':
    app.run()
