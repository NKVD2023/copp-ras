from flask import request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission
from app.utils import log_action

# ==========================================
# УПРАВЛЕНИЕ ГОТОВЫМИ ШАБЛОНАМИ
# ==========================================

@admin_bp.route('/assign_template_users/<int:template_id>', methods=['POST'])
def assign_template_users(template_id):
    """Назначение прав: кто из учреждений должен сдавать этот отчет."""
    template = ReportTemplate.query.get_or_404(template_id)
    template.assigned_users = [] # Очищаем старые доступы
    
    for u_id in request.form.getlist('user_ids'):
        user = User.query.get(u_id)
        if user:
            template.assigned_users.append(user)
            
    db.session.commit()
    log_action('Назначение исполнителей отчета', f'Изменены исполнители для отчета {template.short_name}')
    return redirect(request.referrer or url_for('reports.dashboard'))

@admin_bp.route('/toggle_publish/<int:template_id>', methods=['POST'])
def toggle_publish(template_id):
    """Переключение статуса (Черновик <-> Опубликовано)."""
    template = ReportTemplate.query.get_or_404(template_id)
    template.is_published = not template.is_published
    db.session.commit()
    status_str = "опубликован" if template.is_published else "скрыт"
    log_action('Публикация отчета', f'Отчет {template.short_name} {status_str}')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/clone_template/<int:template_id>', methods=['POST'])
def clone_template(template_id):
    """Копирование структуры старого отчета в новый период."""
    original = ReportTemplate.query.get_or_404(template_id)
    deadline_str = request.form.get('new_deadline')
    deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
    
    new_template = ReportTemplate(
        name=request.form.get('new_name'),
        short_name=request.form.get('new_short_name'),
        period=request.form.get('new_period'),
        deadline=deadline_date,
        is_published=False,
        schema=original.schema
    )
    db.session.add(new_template)
    db.session.commit()
    log_action('Копирование отчета', f'Создана копия отчета {original.short_name} с новым именем {new_template.short_name}')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/delete_template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    """Полное удаление отчета (доступно только Admin)."""
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Очищаем связанные ответы, чтобы не было конфликтов БД
    ReportSubmission.query.filter_by(template_id=template_id).delete()
    name = template.short_name
    db.session.delete(template)
    db.session.commit()
    log_action('Удаление отчета', f'Отчет {name} удален')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/edit_template_meta/<int:template_id>', methods=['POST'])
def edit_template_meta(template_id):
    """Быстрое редактирование названий и сроков отчета через модальное окно."""
    template = ReportTemplate.query.get_or_404(template_id)
    
    template.short_name = request.form.get('short_name')
    template.name = request.form.get('name')
    template.period = request.form.get('period')
    
    deadline_str = request.form.get('deadline')
    template.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
    
    db.session.commit()
    log_action('Редактирование отчета', f'Изменены метаданные отчета {template.short_name}')
    # Возвращаемся обратно на вкладку отчетов
    return redirect(url_for('admin.dashboard') + '#reportsTab')