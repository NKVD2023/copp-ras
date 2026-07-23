"""
Модуль администратора: Управление Готовыми Шаблонами (Admin - Templates).
Включает в себя логику публикации шаблонов, назначения исполнителей,
клонирования отчетов на новый период, редактирования метаданных и удаления.
Также содержит логику экспорта списка должников в Excel.
"""
from flask import request, redirect, url_for, send_file
from flask_login import login_required, current_user
import openpyxl
from io import BytesIO
from datetime import datetime
from app import db
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission
from app.utils import log_action

# ==========================================
# УПРАВЛЕНИЕ ГОТОВЫМИ ШАБЛОНАМИ
# ==========================================

@admin_bp.route('/assign_template_users/<int:template_id>', methods=['POST'])
@login_required
def assign_template_users(template_id):
    """
    Назначение прав доступа: какие учреждения (пользователи) должны сдавать этот отчет.
    Получает массив `user_ids` из формы (список галочек).
    """
    template = ReportTemplate.query.get_or_404(template_id)
    template.assigned_users = [] # Очищаем старые доступы перед добавлением новых
    
    for u_id in request.form.getlist('user_ids'):
        user = User.query.get(u_id)
        if user and user not in template.assigned_users:
            template.assigned_users.append(user)

    for group_name in request.form.getlist('group_names'):
        users_in_group = User.query.filter_by(group=group_name).all()
        for user in users_in_group:
            if user not in template.assigned_users:
                template.assigned_users.append(user)
            
    db.session.commit()
    log_action('Назначение исполнителей отчета', f'Изменены исполнители для отчета {template.short_name}')
    return redirect(request.referrer or url_for('reports.dashboard'))

@admin_bp.route('/toggle_publish/<int:template_id>', methods=['POST'])
@login_required
def toggle_publish(template_id):
    """
    Переключение статуса видимости отчета для пользователей (Черновик <-> Опубликовано).
    Пока отчет не опубликован, пользователи его не увидят на своем дашборде.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    template.is_published = not template.is_published
    
    if template.is_published:
        # Check if a pure template with this name already exists
        existing_pure = ReportTemplate.query.filter_by(name=template.name, is_template=True).first()
        if not existing_pure:
            # Create a pure template
            pure_template = ReportTemplate(
                name=template.name,
                short_name=template.short_name,
                period=None,
                deadline=None,
                is_published=False,
                is_template=True,
                schema=template.schema
            )
            db.session.add(pure_template)
            
    db.session.commit()
    status_str = "опубликован" if template.is_published else "скрыт"
    log_action('Публикация отчета', f'Отчет {template.short_name} {status_str}')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/toggle_archive/<int:template_id>', methods=['POST'])
@login_required
def toggle_archive(template_id):
    """
    Переключение статуса архивации отчета (В архиве <-> Активный).
    Архивированные отчеты скрыты с главного дашборда по умолчанию.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    template.is_archived = not template.is_archived
    db.session.commit()
    status_str = "в архив" if template.is_archived else "из архива"
    log_action('Архивация отчета', f'Отчет {template.short_name} перенесен {status_str}')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/archive_submission/<int:submission_id>', methods=['POST'])
@login_required
def archive_submission(submission_id):
    """
    Архивация сданного отчета
    """
    from app.models import ReportSubmission
    sub = ReportSubmission.query.get_or_404(submission_id)
    sub.is_archived = True
    db.session.commit()
    log_action('Архивация сданного отчета', f'Сданный отчет {sub.id} от пользователя {sub.user.username} перенесен в архив')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/clone_template/<int:template_id>', methods=['POST'])
@login_required
def clone_template(template_id):
    """
    Копирование структуры старого отчета в новый период.
    Берет `schema` от старого отчета и создает новый объект ReportTemplate.
    """
    original = ReportTemplate.query.get_or_404(template_id)
    deadline_str = request.form.get('new_deadline')
    deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
    
    action = request.form.get('action', 'draft')
    is_published = (action == 'publish')
    
    new_template = ReportTemplate(
        name=request.form.get('new_name'),
        short_name=request.form.get('new_short_name'),
        period=request.form.get('new_period'),
        deadline=deadline_date,
        is_published=is_published,
        is_template=False,   # Это рабочий отчет (черновик или опубликованный), а не чистый шаблон
        schema=original.schema
    )
    
    # Копируем пользователей, если они были назначены
    for user in original.assigned_users:
        new_template.assigned_users.append(user)
        
    db.session.add(new_template)
    db.session.commit()
    log_action('Копирование отчета', f'Создана копия отчета {original.short_name} с новым именем {new_template.short_name}')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/delete_template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    """
    Полное удаление отчета из системы вместе со всеми ответами пользователей.
    Доступно исключительно администратору.
    """
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Каскадно очищаем связанные ответы пользователей (Submissions),
    # чтобы не было конфликтов внешних ключей (Foreign Key Constraints) БД
    ReportSubmission.query.filter_by(template_id=template_id).delete()
    name = template.short_name
    db.session.delete(template)
    db.session.commit()
    log_action('Удаление отчета', f'Отчет {name} удален')
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/edit_template_meta/<int:template_id>', methods=['POST'])
@login_required
def edit_template_meta(template_id):
    """
    Быстрое редактирование текстовой информации (метаданных) отчета
    через модальное окно на вкладке отчетов (без захода в конструктор).
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    template.short_name = request.form.get('short_name')
    template.name = request.form.get('name')
    template.period = request.form.get('period')
    
    deadline_str = request.form.get('deadline')
    template.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
    
    db.session.commit()
    log_action('Редактирование отчета', f'Изменены метаданные отчета {template.short_name}')
    # Возвращаемся обратно на вкладку отчетов с якорем
    return redirect(url_for('admin.dashboard') + '#reportsTab')

@admin_bp.route('/export_debtors/<int:template_id>', methods=['GET'])
@login_required
def export_debtors(template_id):
    """
    Формирует и отдает Excel файл (.xlsx) со списком учреждений (должников),
    которые еще не сдали отчет по конкретному шаблону.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Ищем тех, кто уже сдал
    submitted_user_ids = [sub.user_id for sub in ReportSubmission.query.filter_by(template_id=template.id).all()]
    # Вычитаем сдавших из всех назначенных
    debtors = [u for u in template.assigned_users if u.id not in submitted_user_ids]

    # Генерируем Excel-файл в оперативной памяти (BytesIO)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Должники"
    ws.append(["Организация", "Описание"])
    
    for d in debtors:
        ws.append([d.username, d.description or ""])
        
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Должники_{template.short_name}.xlsx".replace(" ", "_")
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )