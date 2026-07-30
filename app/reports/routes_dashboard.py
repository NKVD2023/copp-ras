"""
Модуль отчетов: Дашборд пользователя (Reports - Dashboard).
Отвечает за отображение главной панели для обычного пользователя (учреждения),
на которой показаны назначенные ему отчеты: сданные и ожидающие сдачи.
"""
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from datetime import date
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission, User
from app.utils import is_mobile

# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРДЫ)
# ==========================================

@reports_bp.route('/')
@login_required
def dashboard():
    """
    Отображение главной панели.
    - Администраторов и наблюдателей автоматически перекидывает в админ-панель.
    - Обычному пользователю (учреждению) показывает карточки с отчетами,
      разделенные на две категории: "К заполнению" и "Завершенные".
    """
    if current_user.role in ['admin', 'manager']:
        return redirect(url_for('admin.dashboard'))
        
    # === ЛОГИКА ДЛЯ УЧРЕЖДЕНИЯ (USER) ===
    # Получаем все сданные отчеты напрямую из таблицы отправленных данных
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    
    # Архив пользователя: собираем сами шаблоны из отправленных данных
    filled = [s.template for s in submissions if s.template is not None]
    
    # Активные отчеты: назначенные, опубликованные и еще не сданные
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    unfilled = [t for t in assigned if t.id not in filled_ids]
    
    # Сортируем невыполненные по дедлайну (сначала те, что нужно сдать раньше)
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    overdue = []
    active = []
    
    for t in unfilled:
        if t.deadline and t.deadline < date.today():
            overdue.append(t)
        else:
            active.append(t)
    
    # Собираем все прикрепленные файлы из назначенных и сданных отчетов
    files_list = []
    seen_file_ids = set()
    for t in (unfilled + filled):
        for file in t.attachments:
            if file.id not in seen_file_ids:
                files_list.append({
                    'file': file,
                    'template_name': t.name
                })
                seen_file_ids.add(file.id)

    # Сортируем файлы по дате загрузки (сначала новые)
    files_list.sort(key=lambda x: x['file'].upload_date, reverse=True)
    
    template_name = 'mobile/user_dashboard.html' if is_mobile(request) else 'user_dashboard.html'
    return render_template(template_name, 
                           unfilled_templates=active,
                           overdue_templates=overdue,
                           filled_templates=filled, 
                           attached_files=files_list,
                           current_date=date.today())