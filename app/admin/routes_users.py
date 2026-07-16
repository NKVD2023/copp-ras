"""
Модуль администратора: Управление Пользователями (Admin - Users).
Содержит логику создания, удаления пользователей, принудительного сброса паролей
и массового назначения отчетов конкретному пользователю.
"""
from flask import request, redirect, url_for, flash
from flask_login import current_user
from app import db
from app.admin import admin_bp
from app.models import User, ReportSubmission, ReportTemplate
from app.utils import log_action

# ==========================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ==========================================

@admin_bp.route('/create_user', methods=['POST'])
def create_user():
    """
    Создание нового аккаунта. 
    Роль по умолчанию: 'user' (учреждение, сдающее отчет).
    Также может создавать роль 'viewer' (наблюдатель - только чтение).
    """
    username = request.form.get('username').strip()
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    description = request.form.get('description', '').strip()

    if User.query.filter_by(username=username).first():
        flash('Пользователь с таким логином уже существует')
        return redirect(url_for('admin.dashboard'))
        
    user = User(username=username, role=role, description=description) 
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_action('Создание пользователя', f'Создан новый пользователь: {username} с ролью {role}')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """
    Удаление пользователя и каскадное удаление всех его сданных отчетов.
    Вызывается из вкладки "Пользователи".
    """
    user = User.query.get_or_404(user_id)
    # Очищаем связанные данные, чтобы не сломать внешние ключи
    ReportSubmission.query.filter_by(user_id=user.id).delete()
    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action('Удаление пользователя', f'Пользователь {username} и все его отчеты удалены')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reset_password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    """Принудительный сброс пароля пользователя администратором (если тот забыл)."""
    user = User.query.get_or_404(user_id)
    user.set_password(request.form.get('new_password'))
    db.session.commit()
    log_action('Сброс пароля', f'Сброшен пароль для пользователя {user.username}')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/change_my_password', methods=['POST'])
def change_my_password():
    """Смена собственного пароля (вызывается через модальное окно профиля)."""
    new_password = request.form.get('new_password')
    if new_password:
        current_user.set_password(new_password)
        db.session.commit()
        log_action('Смена пароля', f'Пользователь {current_user.username} сменил свой пароль')
    # request.referrer позволяет вернуть пользователя на ту страницу, где он был
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/assign_access', methods=['POST'])
def assign_access():
    """
    Массовое назначение шаблонов отчетов конкретному пользователю.
    Вызывается из профиля пользователя во вкладке "Пользователи".
    """
    user = User.query.get_or_404(request.form.get('user_id'))
    user.assigned_templates = [] # Очищаем старые доступы
    
    # Назначаем новые на основе отмеченных чекбоксов
    for t_id in request.form.getlist('template_ids'):
        template = ReportTemplate.query.get(t_id)
        if template:
            user.assigned_templates.append(template)
            
    db.session.commit()
    log_action('Назначение доступа', f'Обновлены доступы к отчетам для пользователя {user.username}')
    # Возвращаемся на вкладку с пользователями с якорем
    return redirect(url_for('admin.dashboard') + '#usersTab')