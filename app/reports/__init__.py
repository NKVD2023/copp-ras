from flask import Blueprint

# Создаем единый Blueprint для раздела отчетов
reports_bp = Blueprint('reports', __name__)

# Импортируем файлы маршрутов в самом низу, чтобы избежать циклических импортов
from app.reports import routes_dashboard, routes_fill, routes_data, routes_import