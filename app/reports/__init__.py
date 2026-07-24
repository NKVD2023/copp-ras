"""
Инициализация модуля отчетов (Reports).
Отвечает за просмотр дашборда пользователями, заполнение отчетов,
сборку общих данных (сводная таблица) и экспорт результатов в Excel.
"""
from flask import Blueprint

# Создаем единый Blueprint для раздела отчетов
reports_bp = Blueprint('reports', __name__)

# Импортируем файлы маршрутов в самом низу, чтобы избежать циклических импортов
from app.reports import routes_dashboard, routes_fill, routes_data, routes_import, routes_files