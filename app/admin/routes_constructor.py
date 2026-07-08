from flask import render_template, request, redirect, url_for, jsonify
from flask_login import login_required
from datetime import datetime
from app import db
from app.admin import admin_bp
from app.models import User, ReportTemplate
from app.utils import log_action

# ==========================================
# КОНСТРУКТОР И РЕДАКТОР СТРУКТУРЫ ОТЧЕТОВ
# ==========================================

@admin_bp.route('/constructor', methods=['GET', 'POST'])
def constructor():
    """Создание абсолютно нового отчета с нуля."""
    if request.method == 'POST':
        data = request.get_json()
        deadline_str = data.get('deadline')
        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        
        template = ReportTemplate(
            name=data['name'], 
            short_name=data['short_name'], 
            period=data.get('period'),
            deadline=deadline_date,
            is_published=False,
            schema=data['schema'] # Сохраняем JSON-структуру листов
        )
        db.session.add(template)
        
        # Назначаем пользователей, выбранных в галочках
        for u_id in data.get('user_ids', []):
            user = User.query.get(u_id)
            if user:
                template.assigned_users.append(user)
                
        db.session.commit()
        log_action('Создание отчета (Конструктор)', f'Создан новый шаблон отчета: {template.short_name}')
        return jsonify({'status': 'success'})
        
    # GET запрос - просто отдаем пустую страницу конструктора
    users = User.query.filter(User.role == 'user').all()
    return render_template('constructor.html', users=users)

@admin_bp.route('/edit_constructor/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_constructor(template_id):
    """
    Редактирование существующего отчета. 
    Перезаписывает старые данные новыми из конструктора.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        data = request.get_json()
        deadline_str = data.get('deadline')
        
        # Обновляем мета-информацию и структуру
        template.name = data['name']
        template.short_name = data['short_name']
        template.period = data.get('period')
        template.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        template.schema = data['schema']
        
        # Полностью пересобираем список назначенных пользователей
        template.assigned_users = []
        for u_id in data.get('user_ids', []):
            user = User.query.get(u_id)
            if user:
                template.assigned_users.append(user)
                
        db.session.commit()
        log_action('Редактирование структуры отчета', f'Обновлена структура шаблона отчета: {template.short_name}')
        return jsonify({'status': 'success'})

    # GET запрос - загружаем форму и передаем в неё старый шаблон
    users = User.query.filter(User.role == 'user').all()
    return render_template('constructor.html', users=users, template=template)

@admin_bp.route('/constructor/import_excel', methods=['POST'])
@login_required
def import_excel_template():
    """
    Принимает Excel файл, парсит листы и первую строку,
    создает черновой ReportTemplate и возвращает его ID.
    Пользователь затем будет перенаправлен в редактор.
    """
    import openpyxl
    import time
    
    file = request.files.get('file')
    if not file or not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'status': 'error', 'message': 'Пожалуйста, загрузите файл .xlsx или .xls'}), 400

    try:
        if file.filename.endswith('.xls'):
            import tempfile
            import os
            from xls2xlsx import XLS2XLSX
            
            # Сохраняем загруженный файл во временный .xls
            with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tf_xls:
                file.save(tf_xls.name)
                temp_xls = tf_xls.name
                
            # Конвертируем .xls в .xlsx
            x2x = XLS2XLSX(temp_xls)
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tf_xlsx:
                temp_xlsx = tf_xlsx.name
                
            x2x.to_xlsx(temp_xlsx)
            
            # Загружаем сконвертированный файл
            wb = openpyxl.load_workbook(temp_xlsx, data_only=True)
            
            # Подчищаем временные файлы
            os.remove(temp_xls)
            os.remove(temp_xlsx)
        else:
            wb = openpyxl.load_workbook(file, data_only=True)
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Ошибка при чтении Excel: {str(e)}'}), 400

    schema = []
    
    for sheet_idx, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        fields = []
        
        # 1. Находим реальное количество колонок (max_col) в первых 30 строках
        actual_max_col = 0
        for r in range(1, min(ws.max_row + 1, 30)):
            for c in range(1, ws.max_column + 1):
                if ws.cell(row=r, column=c).value is not None:
                    actual_max_col = max(actual_max_col, c)
                    
        if actual_max_col < 1:
            continue
            
        # Detect header boundary
        header_max_row = min(ws.max_row, 30)
        for r in range(1, header_max_row + 1):
            vals = [str(ws.cell(row=r, column=c).value).strip() for c in range(1, actual_max_col + 1) if ws.cell(row=r, column=c).value is not None]
            if not vals: continue
            
            # Detect numbering row (e.g. 1, 2, 3...)
            if len(vals) >= 3 and vals[0] == '1' and vals[1] == '2' and vals[2] == '3':
                header_max_row = r
                break
            if len(vals) >= 2 and vals[0] == '1' and vals[1] == '2':
                short_count = sum(1 for v in vals if len(v) <= 5)
                if short_count / len(vals) > 0.5:
                    header_max_row = r
                    break
            
        def get_merge_info(r, c):
            for merge_range in ws.merged_cells.ranges:
                if merge_range.min_row <= r <= merge_range.max_row and \
                   merge_range.min_col <= c <= merge_range.max_col:
                    return {
                        'val': ws.cell(row=merge_range.min_row, column=merge_range.min_col).value,
                        'width': merge_range.max_col - merge_range.min_col + 1
                    }
            return {'val': ws.cell(row=r, column=c).value, 'width': 1}

        # 2. Собираем составные заголовки
        for col_idx in range(1, actual_max_col + 1):
            parts = []
            empty_count = 0
            
            for row_idx in range(1, header_max_row + 1):
                info = get_merge_info(row_idx, col_idx)
                val = info['val']
                width = info['width']
                
                v_str = str(val).strip().replace('\n', ' ') if val is not None else ""
                
                if v_str:
                    empty_count = 0
                    # Пропускаем глобальные заголовки (которые растянуты на бОльшую часть таблицы)
                    if width > actual_max_col * 0.75 and width > 2:
                        continue
                    
                    # Избегаем дублирования при вертикальном объединении ячеек
                    if v_str not in parts:
                        parts.append(v_str)
                else:
                    empty_count += 1
                    
                # Если 3 пустые ячейки подряд — считаем, что шапка закончилась
                if empty_count >= 3:
                    break
                    
            label = " - ".join(parts)
            
            if label:
                lower_label = label.lower()
                # Пропускаем служебные колонки
                if 'организация' in lower_label and len(label) < 30:
                    continue
                if lower_label in ['№', '№ п/п', 'n', 'п/п', '№ п\п', 'номер']:
                    continue
                    
                timestamp = str(int(time.time() * 1000))[-6:]
                field_name = f"s{sheet_idx}_c{col_idx}_{timestamp}"
                
                fields.append({
                    'name': field_name,
                    'label': label,
                    'type': 'text',  # Всегда текст по умолчанию
                    'required': False
                })
                
        # Добавляем лист только если на нем есть колонки
        if fields:
            schema.append({
                'sheet_title': sheet_name,
                'fields': fields
            })
            
    wb.close()
    
    if not schema:
        return jsonify({'status': 'error', 'message': 'Не удалось найти таблицы с заголовками в файле.'}), 400
        
    # Создаем черновой шаблон
    base_name = file.filename.rsplit('.', 1)[0]
    
    template = ReportTemplate(
        name=base_name,
        short_name=base_name[:30],
        is_published=False,
        schema=schema
    )
    db.session.add(template)
    db.session.commit()
    
    log_action('Импорт структуры из Excel', f'Загружен шаблон из файла {file.filename}')
    
    return jsonify({
        'status': 'success',
        'template_id': template.id
    })