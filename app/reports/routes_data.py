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
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    
    # Получаем все сданные ответы по данному шаблону
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
    
    # Сортируем по имени организации для удобства поиска
    submissions.sort(key=lambda x: x.user.username.lower())
        
    return render_template('report_data_view.html', template=template, submissions=submissions)

@reports_bp.route('/inline_update/<int:template_id>', methods=['POST'])
@login_required
def inline_update(template_id):
    """
    Сохранение изменений напрямую из сводной таблицы (inline editing).
    Принимает JSON с изменениями (список словарей или один словарь) и обновляет поле `data`.
    """
    if current_user.role not in ['admin', 'viewer']:
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
    """
    Генерация Excel-файла (.xlsx) со всеми ответами учреждений по выбранному шаблону.
    - Динамически создает листы (по вкладкам шаблона).
    - Применяет визуальное форматирование: стили шапки, границы, автоширину колонок.
    - Автоматически подсчитывает строку "Итого" для всех числовых полей.
    """
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()

    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Удаляем стандартный пустой лист 'Sheet'

    # --- НАСТРОЙКИ СТИЛЕЙ EXCEL ---
    title_font = Font(name='Arial', size=14, bold=True, color="000000")
    header_font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="0071DC") # Синяя заливка
    data_font = Font(name='Arial', size=11)
    total_font = Font(name='Arial', size=11, bold=True)
    total_fill = PatternFill("solid", fgColor="F8F9FA") # Светло-серая заливка
    
    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # --- ГЕНЕРАЦИЯ ЛИСТОВ ---
    for sheet_data in template.schema:
        # Excel не поддерживает спецсимволы в названиях листов и ограничивает длину 31 символом
        safe_title = re.sub(r'[\\*?:/\[\]]', '', sheet_data['sheet_title'])[:31]
        ws = wb.create_sheet(title=safe_title)

        # Количество колонок = Организация (1) + Количество полей
        max_col = len(sheet_data['fields']) + 1

        # 1. ЗАГОЛОВОК ОТЧЕТА (Объединенная ячейка на самом верху)
        title_cell = ws.cell(row=1, column=1, value=template.name)
        title_cell.font = title_font
        title_cell.alignment = align_center
        
        for col in range(1, max_col + 1):
            ws.cell(row=1, column=col).border = thin_border
            
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        ws.row_dimensions[1].height = 100 

        # 2. ШАПКА ТАБЛИЦЫ (Названия полей)
        headers = ['Наименование образовательного учреждения'] + [f['label'] for f in sheet_data['fields']]
        ws.append(headers) 
        ws.row_dimensions[2].height = 100

        # Настройка ширины колонок
        ws.column_dimensions['A'].width = 50 
        for col_idx in range(2, max_col + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 45

        # Стилизация шапки
        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = thin_border

        # 3. ДАННЫЕ (Ответы учреждений)
        current_row = 3
        for sub in submissions:
            # Вычисляем максимальное количество строк для этого учреждения (из-за мульти-полей)
            max_rows = 1
            for f in sheet_data['fields']:
                val = sub.data.get(f['name'])
                if isinstance(val, list):
                    max_rows = max(max_rows, len(val))
            
            # Подготавливаем данные для каждой подстроки
            for r_idx in range(max_rows):
                row_data = [sub.user.description if r_idx == 0 else ""]
                for f in sheet_data['fields']:
                    val = sub.data.get(f['name'], '-')
                    
                    if isinstance(val, list):
                        v = val[r_idx] if r_idx < len(val) else '-'
                    else:
                        v = val if r_idx == 0 else ""
                    
                    # Конвертируем строки в числа, если поле числовое, для корректной работы Excel-формул
                    if f['type'] == 'number' and v not in ['-', '', None]:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                    row_data.append(v)
                    
                ws.append(row_data)
                
                # Стилизация данных
                for col_idx, _ in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row + r_idx, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx == 1 else align_center

            # Объединяем ячейку с названием учреждения по вертикали, если строк > 1
            if max_rows > 1:
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row + max_rows - 1, end_column=1)
                
            current_row += max_rows

        # 4. ИТОГО (Вычисление суммы по колонкам)
        total_row = ['Итого']
        for f in sheet_data['fields']:
            if f['type'] == 'number':
                col_total = 0
                has_data = False
                for sub in submissions:
                    val = sub.data.get(f['name'])
                    if val:
                        vals = val if isinstance(val, list) else [val]
                        for v in vals:
                            if v not in ['-', '', None]:
                                try:
                                    col_total += float(v)
                                    has_data = True
                                except ValueError:
                                    pass
                total_row.append(col_total if has_data else 0)
            else:
                total_row.append('-') # Текстовые поля не суммируем

        ws.append(total_row)
        ws.row_dimensions[current_row].height = 40
        
        # Стилизация строки 'Итого'
        for col_idx, _ in enumerate(total_row, 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = thin_border
            cell.alignment = align_left if col_idx == 1 else align_center

    # Формируем и отдаем файл из оперативной памяти
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Свод_{template.short_name}.xlsx".replace(" ", "_")

    log_action('Экспорт данных', f'Скачан Excel файл по отчету {template.short_name}')

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )