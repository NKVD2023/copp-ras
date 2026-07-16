"""
Модуль отчетов: Заполнение отчетов (Reports - Fill).
Предоставляет интерфейс для ввода данных (показателей) пользователями
в соответствии со схемой шаблона. Обрабатывает AJAX-запросы на сохранение.
"""
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
    GET: Отрисовывает форму на основе JSON-схемы шаблона.
    POST: Принимает заполненные данные в виде JSON (AJAX-запрос) и сохраняет в БД.
    Проверяет права доступа, статус публикации и блокировку по дедлайну.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Защита от посторонних (только user), от неопубликованных форм и от отсутствия прав (assigned)
    if current_user.role != 'user' or template not in current_user.assigned_templates or not template.is_published:
        return "Доступ ограничен или форма не опубликована", 403
        
    # Блокировка редактирования, если прошел срок сдачи
    is_locked = template.deadline and date.today() > template.deadline
    
    # Пробуем найти уже существующий ответ (черновик), чтобы предзаполнить форму
    submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
    
    # Сохранение данных (AJAX запрос из JS)
    if request.method == 'POST':
        if is_locked:
            return jsonify({'status': 'error', 'message': 'Дедлайн прошел. Редактирование запрещено.'}), 403
            
        if not submission:
            # Создаем новую запись, если её не было
            submission = ReportSubmission(template_id=template.id, user_id=current_user.id)
            db.session.add(submission)
            
        submission.data = request.get_json()
        db.session.commit()
        log_action('Заполнение отчета', f'Отправлены данные для отчета {template.short_name}')
        return jsonify({'status': 'success'})
        
    # Отрисовка формы для пользователя (GET запрос)
    return render_template('fill_report.html', template=template, submission=submission, is_locked=is_locked)

@reports_bp.route('/fill/<int:template_id>/previous_data', methods=['GET'])
@login_required
def get_previous_data(template_id):
    """
    Возвращает данные из самого свежего предыдущего отчета с таким же short_name.
    Используется для кнопки "Без изменений".
    Сортировка по deadline (строгая дата) по убыванию.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    if current_user.role != 'user' or template not in current_user.assigned_templates:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    # Ищем предыдущий шаблон с таким же short_name, но другим ID
    # Сортируем по deadline по убыванию (сначала самые свежие)
    previous_template = ReportTemplate.query.filter_by(short_name=template.short_name) \
                                            .filter(ReportTemplate.id != template.id) \
                                            .order_by(ReportTemplate.deadline.desc().nullslast(), ReportTemplate.id.desc()) \
                                            .first()
                                            
    if not previous_template:
        return jsonify({'status': 'error', 'message': 'Предыдущий период для данного отчета не найден.'}), 404
        
    # Ищем заполненные данные пользователя в этом предыдущем отчете
    prev_submission = ReportSubmission.query.filter_by(template_id=previous_template.id, user_id=current_user.id).first()
    
    if not prev_submission or not prev_submission.data:
        return jsonify({'status': 'error', 'message': 'Вы не заполняли (или не сохраняли данные) в предыдущем периоде этого отчета.'}), 404
        
    return jsonify({
        'status': 'success',
        'data': prev_submission.data,
        'message': f'Данные из отчета "{previous_template.period or previous_template.name}" успешно загружены.'
    })