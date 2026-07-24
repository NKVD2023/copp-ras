"""
Модуль администратора: Конструктор отчетов (Admin - Constructor).
Содержит логику создания и редактирования структуры шаблонов отчетов,
а также функционал импорта структуры из загруженного Excel-файла.
"""
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
    """
    Маршрут создания абсолютно нового шаблона отчета с нуля.
    GET: Отдает пустую HTML-страницу конструктора.
    POST: Принимает JSON со структурой отчета (название, дедлайн, структура полей `schema`)
          и сохраняет новый шаблон в базу данных.
    """
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
            is_template=False,
            schema=data['schema'] # Сохраняем JSON-структуру листов
        )
        db.session.add(template)
        
        # Создаем чистый шаблон "на будущее"
        pure_template = ReportTemplate(
            name=data['name'], 
            short_name=data['short_name'], 
            period=None,
            deadline=None,
            is_published=False,
            is_template=True,
            schema=data['schema']
        )
        db.session.add(pure_template)
        
        # Назначаем пользователей, выбранных галочками на фронтенде
        for u_id in data.get('user_ids', []):
            user = User.query.get(u_id)
            if user and user not in template.assigned_users:
                template.assigned_users.append(user)
                
        # Назначаем пользователей по выбранным группам
        for group_name in data.get('group_names', []):
            users_in_group = User.query.filter_by(group=group_name).all()
            for user in users_in_group:
                if user not in template.assigned_users:
                    template.assigned_users.append(user)
                
        db.session.commit()
        log_action('Создание отчета (Конструктор)', f'Создан новый шаблон отчета: {template.short_name}')
        return jsonify({'status': 'success'})
        
    # GET запрос - просто отдаем пустую страницу конструктора
    users = User.query.filter(User.role == 'user').all()
    
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']
        
    return render_template('constructor.html', users=users, all_groups=all_groups)

@admin_bp.route('/edit_constructor/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_constructor(template_id):
    """
    Маршрут редактирования существующего шаблона отчета. 
    GET: Загружает форму конструктора, предварительно заполнив её старой `schema`.
    POST: Принимает обновленный JSON и перезаписывает старые данные.
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
        
        # Полностью пересобираем список назначенных пользователей (удаляем старые, добавляем новые)
        template.assigned_users = []
        for u_id in data.get('user_ids', []):
            user = User.query.get(u_id)
            if user and user not in template.assigned_users:
                template.assigned_users.append(user)
                
        for group_name in data.get('group_names', []):
            users_in_group = User.query.filter_by(group=group_name).all()
            for user in users_in_group:
                if user not in template.assigned_users:
                    template.assigned_users.append(user)
                
        db.session.commit()
        log_action('Редактирование структуры отчета', f'Обновлена структура шаблона отчета: {template.short_name}')
        return jsonify({'status': 'success'})

    # GET запрос - загружаем форму и передаем в неё старый шаблон
    users = User.query.filter(User.role == 'user').all()
    
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']
        
    return render_template('constructor.html', users=users, template=template, all_groups=all_groups)

@admin_bp.route('/constructor/import_excel', methods=['POST'])
@login_required
def import_excel_template():
    """
    Маршрут умного парсинга Excel файлов.
    Принимает Excel файл, сканирует его листы, находит шапку таблицы,
    вычленяет столбцы (учитывая горизонтальное и вертикальное объединение ячеек),
    создает черновой ReportTemplate (шаблон) и возвращает его ID на клиент.
    Затем фронтенд перенаправляет пользователя в редактор для тонкой настройки.
    """
    try:
        import openpyxl
        import time
        
        file = request.files.get('file')
        if not file or not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return jsonify({'status': 'error', 'message': 'Пожалуйста, загрузите файл .xlsx или .xls'}), 400

        # Обработка старого формата .xls (конвертация в .xlsx через xls2xlsx)
        if file.filename.endswith('.xls'):
            import tempfile
            import os
            from xls2xlsx import XLS2XLSX
            
            # На Windows файл нужно закрыть перед тем, как file.save() попытается его открыть
            tf_xls = tempfile.NamedTemporaryFile(suffix='.xls', delete=False)
            tf_xls.close()
            temp_xls = tf_xls.name
            
            file.save(temp_xls)
                
            # Конвертируем .xls в .xlsx
            x2x = XLS2XLSX(temp_xls)
            
            tf_xlsx = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            tf_xlsx.close()
            temp_xlsx = tf_xlsx.name
                
            x2x.to_xlsx(temp_xlsx)
            
            # Загружаем сконвертированный файл (data_only=True позволяет считывать значения вместо формул)
            wb = openpyxl.load_workbook(temp_xlsx, data_only=True)
            
            # Подчищаем временные файлы
            os.remove(temp_xls)
            os.remove(temp_xlsx)
        else:
            # Загружаем обычный .xlsx
            wb = openpyxl.load_workbook(file, data_only=True)

        schema = []
        
        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            ws = wb[sheet_name]
            fields = []
            
            # ШАГ 1: Находим реальное количество колонок (max_col), игнорируя полностью пустые крайние столбцы
            actual_max_col = 0
            for r in range(1, min((ws.max_row or 1) + 1, 30)):
                for c in range(1, (ws.max_column or 1) + 1):
                    if ws.cell(row=r, column=c).value is not None:
                        actual_max_col = max(actual_max_col, c)
                        
            if actual_max_col < 1:
                continue
                
            # ЭВРИСТИКА: Пытаемся автоматически определить, где заканчивается шапка таблицы.
            header_max_row = min((ws.max_row or 1), 30)
            for r in range(1, header_max_row + 1):
                vals = [str(ws.cell(row=r, column=c).value).strip() for c in range(1, actual_max_col + 1) if ws.cell(row=r, column=c).value is not None]
                if not vals: continue
                
                # Ищем строку с нумерацией (типа 1, 2, 3...) - это явный признак конца шапки
                if len(vals) >= 3 and vals[0] == '1' and vals[1] == '2' and vals[2] == '3':
                    header_max_row = r
                    break
                # Или если строка содержит короткие цифры (альтернативная нумерация)
                if len(vals) >= 2 and vals[0] == '1' and vals[1] == '2':
                    short_count = sum(1 for v in vals if len(v) <= 5)
                    if short_count / len(vals) > 0.5:
                        header_max_row = r
                        break
                
            def get_merge_info(r, c):
                """Вспомогательная функция для корректного чтения объединенных (Merged) ячеек"""
                for merge_range in ws.merged_cells.ranges:
                    if merge_range.min_row <= r <= merge_range.max_row and \
                       merge_range.min_col <= c <= merge_range.max_col:
                        return {
                            'val': ws.cell(row=merge_range.min_row, column=merge_range.min_col).value,
                            'width': merge_range.max_col - merge_range.min_col + 1
                        }
                return {'val': ws.cell(row=r, column=c).value, 'width': 1}

            # ШАГ 2: Собираем составные заголовки, проходясь по столбцам сверху вниз до конца шапки
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
                        # Пропускаем глобальные "над-заголовки" (которые растянуты на бОльшую часть таблицы)
                        if width > actual_max_col * 0.75 and width > 2:
                            continue
                        
                        # Избегаем дублирования текста при вертикальном объединении ячеек
                        if v_str not in parts:
                            parts.append(v_str)
                    else:
                        empty_count += 1
                        
                    # Если 3 пустые ячейки подряд — считаем, что шапка над этим столбцом закончилась
                    if empty_count >= 3:
                        break
                        
                # Склеиваем найденные части заголовка через дефис
                label = " - ".join(parts)
                
                if label:
                    lower_label = label.lower()
                    # Игнорируем служебные колонки
                    if 'организация' in lower_label and len(label) < 30:
                        continue
                    if lower_label in ['№', '№ п/п', 'n', 'п/п', '№ п\п', 'номер']:
                        continue
                        
                    # Генерируем уникальный внутренний ID поля для JSON
                    timestamp = str(int(time.time() * 1000))[-6:]
                    field_name = f"s{sheet_idx}_c{col_idx}_{timestamp}"
                    
                    fields.append({
                        'name': field_name,
                        'label': label,
                        'type': 'text',  # Все поля при импорте по умолчанию текстовые
                        'required': False
                    })
                    
            # Добавляем лист в структуру отчета только если на нем есть распознанные колонки
            if fields:
                schema.append({
                    'sheet_title': sheet_name,
                    'fields': fields
                })
                
        wb.close()
        
        if not schema:
            return jsonify({'status': 'error', 'message': 'Не удалось найти таблицы с заголовками в файле.'}), 400
            
        # ШАГ 3: Создаем черновой шаблон в БД
        original_filename = file.filename or "Новый шаблон"
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        if not base_name.strip():
            base_name = "Новый шаблон"
        
        template = ReportTemplate(
            name=base_name,
            short_name=base_name[:30],
            is_published=False,
            schema=schema
        )
        db.session.add(template)
        db.session.commit()
        
        log_action('Импорт структуры из Excel', f'Загружен шаблон из файла {file.filename}')
        
        # Возвращаем ID шаблона на клиент для последующего перенаправления в редактор
        return jsonify({
            'status': 'success',
            'template_id': template.id
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Системная ошибка обработки файла: {str(e)}'}), 500