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
    - Админа перекидывает в админку.
    - Наблюдателю показывает все шаблоны и должников.
    - Обычному пользователю (учреждению) показывает, что нужно сдать, а что уже сдано.
    """
    if current_user.role in ['admin', 'viewer']:
        return redirect(url_for('admin.dashboard'))
        
    # === ЛОГИКА ДЛЯ УЧРЕЖДЕНИЯ (USER) ===
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    
    unfilled = [t for t in assigned if t.id not in filled_ids]
    filled = [t for t in assigned if t.id in filled_ids]
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    return render_template('user_dashboard.html', unfilled_templates=unfilled, filled_templates=filled, current_date=date.today())