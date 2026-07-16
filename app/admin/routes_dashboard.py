"""
Модуль администратора: Главная панель (Admin - Dashboard).
Отвечает за сбор всей статистики, отображение списков пользователей, отчетов,
бэкапов и логов. Также содержит глобальную функцию проверки прав для всех admin-маршрутов.
"""
import os
import datetime
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission, ActionLog
from app import db
from config import basedir

# ==========================================
# ПРОВЕРКА ПРАВ ДОСТУПА ДЛЯ ВСЕХ МАРШРУТОВ
# ==========================================
@admin_bp.before_request
@login_required
def require_admin():
    """
    Middleware: Перехватывает каждый запрос к админ-панели (с префиксом /admin).
    - Если пользователь 'admin' -> пропускает дальше.
    - Если пользователь 'viewer' (наблюдатель) -> пускает только на чтение отчетов.
    - Всех остальных (обычных пользователей) выкидывает на их личный дашборд.
    """
    if current_user.role == 'admin':
        return
        
    # Разрешенные маршруты для роли "наблюдатель"
    allowed_for_viewer = ['admin.dashboard', 'admin.constructor', 'admin.edit_constructor', 'admin.toggle_publish', 'admin.clone_template', 'admin.assign_template_users', 'admin.import_excel_template', 'admin.change_my_password', 'admin.export_debtors', 'admin.edit_template_meta']
    if current_user.role == 'viewer' and request.endpoint in allowed_for_viewer:
        return
        
    return redirect(url_for('reports.dashboard'))

# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРД)
# ==========================================
@admin_bp.route('/')
def dashboard():
    """
    Основной маршрут панели администратора.
    Агрегирует данные из всех таблиц (пользователи, шаблоны, отчеты, логи, бэкапы)
    и передает их в единый шаблон `admin_dashboard.html`, который использует
    систему вкладок (tabs) для их отображения.
    """
    # 1. Данные пользователей (исключая текущего)
    users = User.query.filter(User.id != current_user.id).all()
    
    # 2. Список шаблонов (новые сверху)
    templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    
    # Данные для вкладки "База Данных"
    all_users = User.query.all()
    all_submissions = ReportSubmission.query.all()
    
    # 3. Собираем словарь должников (кто из назначенных пользователей еще не сдал отчет)
    debtors_map = {}
    for t in templates:
        # ID пользователей, которые уже сдали отчет по этому шаблону
        submitted_user_ids = [sub.user_id for sub in ReportSubmission.query.filter_by(template_id=t.id).all()]
        # Должники = Назначенные пользователи МИНУС Сдавшие пользователи
        debtors = [u for u in t.assigned_users if u.id not in submitted_user_ids]
        debtors_map[t.id] = debtors

    # 4. Сканируем папку backups для отображения списка резервных копий
    backups_dir = os.path.join(basedir, 'backups')
    backups_list = []
    if os.path.exists(backups_dir):
        for f in os.listdir(backups_dir):
            if f.endswith('.db'):
                path = os.path.join(backups_dir, f)
                stat = os.stat(path)
                backups_list.append({
                    'name': f,
                    'size': stat.st_size,           # Размер файла
                    'mtime': stat.st_mtime          # Время изменения
                })
        # Сортируем: свежие бэкапы сверху
        backups_list.sort(key=lambda x: x['mtime'], reverse=True)
        
    # 5. Загружаем последние 500 записей журнала действий
    logs_list = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(500).all()

    # Передаем весь этот массив данных в шаблон
    return render_template('admin_dashboard.html', 
                           users=users, 
                           templates=templates, 
                           debtors_map=debtors_map,
                           all_users=all_users,
                           all_submissions=all_submissions,
                           backups_list=backups_list,
                           logs_list=logs_list,
                           current_date=datetime.date.today())

@admin_bp.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    """
    Маршрут для полной очистки таблицы `action_logs`.
    Доступен исключительно администратору (viewer не может удалять логи).
    """
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
        
    ActionLog.query.delete()
    db.session.commit()
    
    # Сразу после очистки добавим лог о том, кто именно её произвел
    from app.utils import log_action
    log_action('Очистка логов', f'Администратор {current_user.username} полностью очистил журнал действий')
    
    return redirect(url_for('admin.dashboard') + '#logsTab')