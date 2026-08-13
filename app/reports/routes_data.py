"""
Модуль отчетов: Просмотр и Экспорт данных (Reports - Data).
Предоставляет функционал для администраторов:
- Просмотр сводной HTML-таблицы (все ответы учреждений по одному отчету).
- Встроенное (inline) редактирование ответов прямо в браузере.
- Экспорт всех заполненных данных в сводный Excel файл (.xlsx) с форматированием.
"""
from flask import render_template, send_file, request, jsonify
from flask_login import login_required, current_user
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import re
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission, User
from app import db
from app.utils import log_action

# ==========================================
# ПРОСМОТР И ЭКСПОРТ ДАННЫХ
# ==========================================

@reports_bp.route('/view_data/<int:template_id>')
@login_required
def view_data(template_id):
    """
    Просмотр сводных данных по отчету прямо в браузере (HTML таблица).
    Каждый лист шаблона отображается отдельной вкладкой, столбцы - это поля, 
    строки - это ответившие учреждения.
    """
    if current_user.role not in ['admin', 'manager']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Получаем все сданные ответы по данному шаблону
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
    
    # Сортируем по дате сдачи (сначала новые). Для этого используем id в обратном порядке.
    submissions.sort(key=lambda x: x.id, reverse=True)
    
    from app.utils import build_table_headers
    from app.reports.routes_fill import get_historical_data
    
    has_inactive_fields = False
    inactive_field_names = []
    
    # Обогащаем схему шаблона данными для сложной шапки
    for sheet in template.schema:
        fields = sheet.get('fields', [])
        header_rows, leaf_fields = build_table_headers(fields)
        sheet['header_rows'] = header_rows
        sheet['leaf_fields'] = leaf_fields
        for field in leaf_fields:
            if field.get('is_active') is False:
                has_inactive_fields = True
                inactive_field_names.append(field['name'])

    if has_inactive_fields:
        submitted_user_ids = {s.user_id for s in submissions}
        unsubmitted_users = [u for u in template.assigned_users if u.id not in submitted_user_ids]
        
        class DummySubmission:
            def __init__(self, user, data):
                self.user = user
                self.data = data
                
        for user in unsubmitted_users:
            hist_data = get_historical_data(template, user.id)
            if hist_data:
                dummy_data = {}
                for fname in inactive_field_names:
                    if fname in hist_data:
                        dummy_data[fname] = hist_data[fname]
                submissions.append(DummySubmission(user=user, data=dummy_data))
        
    return render_template('report_data_view.html', template=template, submissions=submissions)

@reports_bp.route('/inline_update/<int:template_id>', methods=['POST'])
@login_required
def inline_update(template_id):
    """
    Сохранение изменений напрямую из сводной таблицы (inline editing).
    Принимает JSON с изменениями (список словарей или один словарь) и обновляет поле `data`.
    """
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    req = request.get_json()
    
    updates = req if isinstance(req, list) else [req]
    
    for item in updates:
        user_id = item.get('user_id')
        field_name = item.get('field_name')
        value = item.get('value')
        
        if not user_id or not field_name:
            continue

        # --- ВАЛИДАЦИЯ ПО СХЕМЕ ШАБЛОНА ---
        # Находим описание поля в схеме, чтобы применить те же правила, что и при обычном сохранении
        import json as _json
        schema = template.schema if not isinstance(template.schema, str) else _json.loads(template.schema or '[]')
        field_def = next(
            (f for sheet in (schema or []) for f in sheet.get('fields', []) if f['name'] == field_name),
            None
        )
        if field_def and value is not None and str(value).strip() != '':
            if field_def.get('is_multiple'):
                if isinstance(value, str):
                    value = [v.strip() for v in value.split('\n') if v.strip()]
                    
            if field_def.get('type') == 'number':
                try:
                    # If it's multiple, we should probably check each, but inline_update only checks scalar currently. Let's adapt:
                    vals_to_check = value if isinstance(value, list) else [value]
                    for v in vals_to_check:
                        num_val = float(v)
                        if num_val < 0:
                            return jsonify({'status': 'error', 'message': f'Поле "{field_def["label"]}" не может быть отрицательным.'}), 400
                except (ValueError, TypeError):
                    return jsonify({'status': 'error', 'message': f'Поле "{field_def["label"]}" должно быть числом.'}), 400
            elif field_def.get('type') == 'text':
                pass
        # -----------------------------------

        submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=user_id).first()
        
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=user_id, data={})
            db.session.add(submission)
            
        # ВАЖНО: Для корректного обнаружения изменений в JSON/JSONB колонках SQLAlchemy
        # необходимо создать новую копию словаря `data`, изменить её и присвоить обратно.
        data_copy = submission.data.copy() if submission.data else {}
        data_copy[field_name] = value
        submission.data = data_copy
    
    db.session.commit()
    log_action('Редактирование данных отчета', f'Внесены изменения в сводной таблице отчета {template.short_name}')
    return jsonify({'status': 'success'})


@reports_bp.route('/export_excel/<int:template_id>')
@login_required
def export_excel(template_id):
    if current_user.role not in ['admin', 'manager']:
        return "Доступ ограничен", 403
        
    from app.services.task_service import TaskService
    task_id = TaskService.start_excel_generation(template_id, current_user.id)
    return jsonify({'status': 'success', 'task_id': task_id})


@reports_bp.route('/export_my_excel/<int:template_id>')
@login_required
def export_my_excel(template_id):
    """
    Генерация Excel-файла (.xlsx) с ответами текущего пользователя.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=current_user.id).first()
    
    if not submission:
        return "Отчет еще не заполнен", 400

    from app.services.excel_service import ExcelService
    from flask import send_file
    
    output, filename = ExcelService.export_report(template, [submission])
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f"Мой_отчет_{filename}"
    )
