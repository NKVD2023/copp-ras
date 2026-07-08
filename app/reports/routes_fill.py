from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission
from app.utils import log_action

# ==========================================
# ЗАПОЛНЕНИЕ ОТЧЕТОВ ПОЛЬЗОВАТЕЛЯМИ
# ==========================================

@reports_bp.route('/fill/<int:template_id>', methods=['GET', 'POST'])
@login_required
def fill_report(template_id):
    """
    Страница, где учреждение вводит свои данные (цифры и текст).
    Проверяет права доступа, статус публикации и не прошел ли дедлайн.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Защита от посторонних и неопубликованных форм
    if current_user.role != 'user' or template not in current_user.assigned_templates or not template.is_published:
        return "Доступ ограничен или форма не опубликована", 403
        
    is_locked = template.deadline and date.today() > template.deadline
    submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
    
    # Сохранение данных (AJAX запрос)
    if request.method == 'POST':
        if is_locked:
            return jsonify({'status': 'error', 'message': 'Дедлайн прошел. Редактирование запрещено.'}), 403
            
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=current_user.id)
            db.session.add(submission)
            
        submission.data = request.get_json()
        db.session.commit()
        log_action('Заполнение отчета', f'Отправлены данные для отчета {template.short_name}')
        return jsonify({'status': 'success'})
        
    # Отрисовка формы (GET запрос)
    return render_template('fill_report.html', template=template, submission=submission, is_locked=is_locked)