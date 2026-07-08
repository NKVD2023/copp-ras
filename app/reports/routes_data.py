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
    """Просмотр сводных данных по отчету прямо в браузере (HTML таблица)."""
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
    
    # Сортируем по имени организации для удобства
    submissions.sort(key=lambda x: x.user.username.lower())
        
    return render_template('report_data_view.html', template=template, submissions=submissions)

@reports_bp.route('/inline_update/<int:template_id>', methods=['POST'])
@login_required
def inline_update(template_id):
    """Сохранение изменений напрямую из сводной таблицы."""
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
            
        submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=user_id).first()
        
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=user_id, data={})
            db.session.add(submission)
            
        # Для SQLite JSON поля необходимо присваивать новый объект словаря
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
    Генерация Excel-файла (.xlsx) со всеми ответами учреждений.
    Применяет форматирование, стили шапки, автоширину колонок и подсчет 'Итого'.
    """
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # --- НАСТРОЙКИ СТИЛЕЙ EXCEL ---
    title_font = Font(name='Arial', size=14, bold=True, color="000000")
    header_font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="0071DC")
    data_font = Font(name='Arial', size=11)
    total_font = Font(name='Arial', size=11, bold=True)
    total_fill = PatternFill("solid", fgColor="F8F9FA")
    
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
        safe_title = re.sub(r'[\\*?:/\[\]]', '', sheet_data['sheet_title'])[:31]
        ws = wb.create_sheet(title=safe_title)

        max_col = len(sheet_data['fields']) + 1

        # 1. ЗАГОЛОВОК
        title_cell = ws.cell(row=1, column=1, value=template.name)
        title_cell.font = title_font
        title_cell.alignment = align_center
        
        for col in range(1, max_col + 1):
            ws.cell(row=1, column=col).border = thin_border
            
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        ws.row_dimensions[1].height = 100 

        # 2. ШАПКА ТАБЛИЦЫ
        headers = ['Организация'] + [f['label'] for f in sheet_data['fields']]
        ws.append(headers) 
        ws.row_dimensions[2].height = 100

        ws.column_dimensions['A'].width = 50 
        for col_idx in range(2, max_col + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 45

        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = thin_border

        # 3. ДАННЫЕ
        current_row = 3
        for sub in submissions:
            row_data = [sub.user.username]
            for f in sheet_data['fields']:
                val = sub.data.get(f['name'], '-')
                if f['type'] == 'number' and val not in ['-', '', None]:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                row_data.append(val)

            ws.append(row_data)
            ws.row_dimensions[current_row].height = 70 

            for col_idx, _ in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = align_left if col_idx == 1 else align_center
            
            current_row += 1

        # 4. ИТОГО
        total_row = ['Итого']
        for f in sheet_data['fields']:
            if f['type'] == 'number':
                col_total = 0
                has_data = False
                for sub in submissions:
                    val = sub.data.get(f['name'])
                    if val:
                        try:
                            col_total += float(val)
                            has_data = True
                        except ValueError:
                            pass
                total_row.append(col_total if has_data else 0)
            else:
                total_row.append('-')

        ws.append(total_row)
        ws.row_dimensions[current_row].height = 40
        
        for col_idx, _ in enumerate(total_row, 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = thin_border
            cell.alignment = align_left if col_idx == 1 else align_center

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