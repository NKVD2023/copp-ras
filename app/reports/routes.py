from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from datetime import date
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import re
from app import db
from app.models import ReportTemplate, ReportSubmission, User

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def dashboard():
    if current_user.role in ['admin', 'viewer']:
        return redirect(url_for('admin.dashboard'))
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    
    unfilled = [t for t in assigned if t.id not in filled_ids]
    filled = [t for t in assigned if t.id in filled_ids]
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    return render_template('base.html', unfilled_templates=unfilled, filled_templates=filled, current_date=date.today())

@reports_bp.route('/fill/<int:template_id>', methods=['GET', 'POST'])
@login_required
def fill_report(template_id):
    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role != 'user' or template not in current_user.assigned_templates or not template.is_published:
        return "Доступ ограничен или форма не опубликована", 403
        
    is_locked = template.deadline and date.today() > template.deadline
    submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
    
    if request.method == 'POST':
        if is_locked:
            return jsonify({'status': 'error', 'message': 'Дедлайн прошел. Редактирование запрещено.'}), 403
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=current_user.id)
            db.session.add(submission)
        submission.data = request.get_json()
        db.session.commit()
        return jsonify({'status': 'success'})
        
    return render_template('fill_report.html', template=template, submission=submission, is_locked=is_locked)

@reports_bp.route('/view_data/<int:template_id>')
@login_required
def view_data(template_id):
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
    return render_template('report_data_view.html', template=template, submissions=submissions)


@reports_bp.route('/export_excel/<int:template_id>')
@login_required
def export_excel(template_id):
    if current_user.role not in ['admin', 'viewer']:
        return "Доступ ограничен", 403
        
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # --- НАСТРОЙКИ СТИЛЕЙ ---
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

    for sheet_data in template.schema:
        safe_title = re.sub(r'[\\*?:/\[\]]', '', sheet_data['sheet_title'])[:31]
        ws = wb.create_sheet(title=safe_title)

        # Вычисляем количество колонок
        max_col = len(sheet_data['fields']) + 1

        # 1. ЗАГОЛОВОК (Полное наименование отчета)
        title_cell = ws.cell(row=1, column=1, value=template.name)
        title_cell.font = title_font
        title_cell.alignment = align_center
        
        # Рисуем рамку для всего заголовка
        for col in range(1, max_col + 1):
            ws.cell(row=1, column=col).border = thin_border
            
        # Объединяем ячейки для заголовка
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        ws.row_dimensions[1].height = 100 # Высокая строка для заголовка

        # 2. ШАПКА ТАБЛИЦЫ
        headers = ['Организация'] + [f['label'] for f in sheet_data['fields']]
        ws.append(headers) # Автоматически добавится на 2-ю строку
        ws.row_dimensions[2].height = 100

        # Ширина колонок (сделали ОЧЕНЬ широкими)
        ws.column_dimensions['A'].width = 50 
        for col_idx in range(2, max_col + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 45

        # Стилизуем шапку (теперь она на 2-й строке)
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
            ws.row_dimensions[current_row].height = 70 # Очень высокие строки для длинных текстов

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

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )