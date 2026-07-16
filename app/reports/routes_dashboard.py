"""
Модуль отчетов: Дашборд пользователя (Reports - Dashboard).
Отвечает за отображение главной панели для обычного пользователя (учреждения),
на которой показаны назначенные ему отчеты: сданные и ожидающие сдачи.
"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import date
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission, User

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
    if current_user.role in ['admin', 'viewer']:
        return redirect(url_for('admin.dashboard'))
        
    # === ЛОГИКА ДЛЯ УЧРЕЖДЕНИЯ (USER) ===
    # Получаем все отчеты, которые пользователь уже сдал
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    
    # Получаем все шаблоны, которые назначены этому пользователю и уже опубликованы
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    
    # Разделяем на те, что еще не заполнены, и те, что заполнены
    unfilled = [t for t in assigned if t.id not in filled_ids]
    filled = [t for t in assigned if t.id in filled_ids]
    
    # Сортируем невыполненные по дедлайну (сначала те, что нужно сдать раньше)
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    return render_template('user_dashboard.html', unfilled_templates=unfilled, filled_templates=filled, current_date=date.today())