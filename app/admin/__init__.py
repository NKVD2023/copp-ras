"""
Модуль административной панели (Admin).
Объединяет все маршруты, связанные с управлением пользователями, шаблонами, конструктором и базой данных.
Регистрация Blueprint происходит здесь.
"""
from flask import Blueprint

# Создаем единый Blueprint для всей админ-панели (с префиксом /admin)
admin_bp = Blueprint('admin', __name__)

# ВАЖНО: Импортируем файлы маршрутов В САМОМ НИЗУ после создания Blueprint.
# Это необходимо, чтобы избежать ошибки "циклического импорта" (Circular Import) в Python,
# так как сами маршруты внутри этих файлов импортируют `admin_bp` отсюда.
from app.admin import routes_dashboard, routes_users, routes_templates, routes_constructor, routes_db, routes_files