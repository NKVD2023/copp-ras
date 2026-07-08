import os
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
    Перехватывает каждый запрос к админ-панели.
    Если пользователь - админ, пускает дальше.
    Если наблюдатель (viewer) - пускает только на разрешенные страницы.
    Всех остальных выкидывает на панель отчетов.
    """
    if current_user.role == 'admin':
        return
        
    allowed_for_viewer = ['admin.constructor', 'admin.toggle_publish', 'admin.clone_template', 'admin.assign_template_users']
    if current_user.role == 'viewer' and request.endpoint in allowed_for_viewer:
        return
        
    return redirect(url_for('reports.dashboard'))

# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРД)
# ==========================================
@admin_bp.route('/')
def dashboard():
    """
    Собирает всю статистику, списки пользователей и шаблонов 
    для отображения на главной странице администратора.
    """
    users = User.query.filter(User.id != current_user.id).all()
    templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    
    # Для модуля базы данных
    all_users = User.query.all()
    all_submissions = ReportSubmission.query.all()
    
    # Собираем словарь должников (кто еще не сдал отчет)
    debtors_map = {}
    for t in templates:
        submitted_user_ids = [sub.user_id for sub in ReportSubmission.query.filter_by(template_id=t.id).all()]
        debtors = [u for u in t.assigned_users if u.id not in submitted_user_ids]
        debtors_map[t.id] = debtors

    
    # Для модуля резервного копирования
    backups_dir = os.path.join(basedir, 'backups')
    backups_list = []
    if os.path.exists(backups_dir):
        for f in os.listdir(backups_dir):
            if f.endswith('.db'):
                path = os.path.join(backups_dir, f)
                stat = os.stat(path)
                backups_list.append({
                    'name': f,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                })
        backups_list.sort(key=lambda x: x['mtime'], reverse=True)
        
    # Для журнала действий
    logs_list = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(500).all()

    return render_template('admin_dashboard.html', 
                           users=users, 
                           templates=templates, 
                           debtors_map=debtors_map,
                           all_users=all_users,
                           all_submissions=all_submissions,
                           backups_list=backups_list,
                           logs_list=logs_list)

@admin_bp.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    """Полная очистка журнала действий (только админ)"""
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
        
    ActionLog.query.delete()
    db.session.commit()
    
    # Сразу после очистки добавим лог о том, кто очистил
    from app.utils import log_action
    log_action('Очистка логов', f'Администратор {current_user.username} полностью очистил журнал действий')
    
    return redirect(url_for('admin.dashboard') + '#logsTab')