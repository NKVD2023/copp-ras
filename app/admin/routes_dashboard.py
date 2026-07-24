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
from app.models import User, ReportTemplate, ReportSubmission, ActionLog, UploadedFile
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
    allowed_for_viewer = ['admin.dashboard', 'admin.constructor', 'admin.edit_constructor', 'admin.toggle_publish', 'admin.toggle_archive', 'admin.clone_template', 'admin.assign_template_users', 'admin.import_excel_template', 'admin.change_my_password', 'admin.export_debtors', 'admin.edit_template_meta', 'admin.upload_file', 'admin.delete_file']
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
    
    sort_param = request.args.get('sort', 'deadline_asc')
    
    # 1. Данные пользователей (исключая текущего)
    users = User.query.filter(User.id != current_user.id).all()
    
    # 2. Список шаблонов (новые сверху)
    all_templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    
    # 3. Собираем словарь должников и распределяем шаблоны
    pure_templates = []
    published_templates = []
    draft_templates = []
    archived_templates = []
    completed_templates = []
    debtors_map = {}
    
    for t in all_templates:
        # ID пользователей, которые уже сдали отчет по этому шаблону
        submitted_user_ids = [sub.user_id for sub in ReportSubmission.query.filter_by(template_id=t.id).all()]
        # Должники = Назначенные пользователи МИНУС Сдавшие пользователи
        debtors = [u for u in t.assigned_users if u.id not in submitted_user_ids]
        debtors_map[t.id] = debtors
        
        if t.is_archived:
            archived_templates.append(t)
        elif t.is_template:
            pure_templates.append(t)
        elif not t.is_published:
            draft_templates.append(t)
        else:
            # Отчет опубликован. Проверяем, сдали ли все
            if t.assigned_users.count() > 0 and len(debtors) == 0:
                completed_templates.append(t)
            else:
                published_templates.append(t)

    # Сортируем все списки
    def sort_templates(templates, sort_by):
        if sort_by == 'deadline_asc':
            return sorted(templates, key=lambda x: x.deadline or datetime.date.max)
        elif sort_by == 'deadline_desc':
            return sorted(templates, key=lambda x: x.deadline or datetime.date.min, reverse=True)
        elif sort_by == 'name_asc':
            return sorted(templates, key=lambda x: x.name.lower())
        elif sort_by == 'name_desc':
            return sorted(templates, key=lambda x: x.name.lower(), reverse=True)
        elif sort_by == 'id_desc':
            return sorted(templates, key=lambda x: x.id, reverse=True)
        return sorted(templates, key=lambda x: x.deadline or datetime.date.max)
        
    pure_templates = sort_templates(pure_templates, sort_param)
    published_templates = sort_templates(published_templates, sort_param)
    draft_templates = sort_templates(draft_templates, sort_param)
    archived_templates = sort_templates(archived_templates, sort_param)
    completed_templates = sort_templates(completed_templates, sort_param)

    # Данные для вкладки "База Данных" и "Сданные отчёты" (если нужны)
    all_users = User.query.all()
    all_submissions = ReportSubmission.query.order_by(ReportSubmission.id.desc()).all()
    active_submissions = [sub for sub in all_submissions if getattr(sub, 'is_archived', False) == False]

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

    # 6. Получение всех уникальных существующих групп
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']

    # 6. Файлы
    all_files = UploadedFile.query.order_by(UploadedFile.upload_date.desc()).all()

    # Передаем весь этот массив данных в шаблон
    return render_template('admin_dashboard.html', 
                           users=users, 
                           templates=all_templates, 
                           pure_templates=pure_templates,
                           published_templates=published_templates,
                           draft_templates=draft_templates,
                           archived_templates=archived_templates,
                           completed_templates=completed_templates,
                           debtors_map=debtors_map,
                           all_users=all_users,
                           all_submissions=all_submissions,
                           active_submissions=active_submissions,
                           backups_list=backups_list,
                           logs_list=logs_list,
                           all_groups=all_groups,
                           all_files=all_files,
                           current_sort=sort_param,
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