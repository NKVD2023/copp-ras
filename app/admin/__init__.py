from flask import Blueprint

# Создаем единый Blueprint для всей админ-панели
admin_bp = Blueprint('admin', __name__)

# ВАЖНО: Импортируем файлы маршрутов В САМОМ НИЗУ.
# Это необходимо, чтобы избежать ошибки "циклического импорта" в Python.
from app.admin import routes_dashboard, routes_users, routes_templates, routes_constructor, routes_db