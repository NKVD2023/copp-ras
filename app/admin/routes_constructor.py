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

@admin_bp.route('/preview_constructor', methods=['POST'])
@login_required
def preview_constructor():
    """
    Маршрут для предпросмотра собираемого шаблона из конструктора.
    Принимает JSON структуры и рендерит fill_report.html в режиме предпросмотра.
    """
    import json
    from app.utils import build_schema_tree
    data = request.form
    schema = build_schema_tree(json.loads(data.get('schema', '[]')))
    name = data.get('name', 'Предпросмотр отчета')
    
    class DummyTemplate:
        def __init__(self, name, schema):
            self.id = 0
            self.name = name
            self.schema = schema
            self.attachments = []
            
    template = DummyTemplate(name, schema)
    
    return render_template('fill_report.html', template=template, schema=schema, is_locked=False, submission=None, is_preview=True)

@admin_bp.route('/constructor', methods=['GET', 'POST'])
@login_required
def constructor():
    """
    Маршрут создания абсолютно нового шаблона отчета с нуля.
    """
    from flask_login import current_user
    from flask import abort
    if current_user.role not in ['admin', 'manager']:
        abort(403)
    if request.method == 'POST':
        import json
        data = request.form
        deadline_str = data.get('deadline')
        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        
        schema = json.loads(data.get('schema', '[]'))
        
        period_data_str = data.get('period_data')
        period_data = json.loads(period_data_str) if period_data_str else None
        
        template = ReportTemplate(
            name=data.get('name'), 
            short_name=data.get('short_name'), 
            period=data.get('period'),
            period_data=period_data,
            deadline=deadline_date,
            is_published=False,
            is_template=True, # Теперь сразу создаем как шаблон
            schema=schema # Сохраняем JSON-структуру листов
        )
        db.session.add(template)
        

        
        # Назначаем пользователей, выбранных галочками на фронтенде
        user_ids = json.loads(data.get('user_ids', '[]'))
        for u_id in user_ids:
            user = User.query.get(u_id)
            if user and user not in template.assigned_users:
                template.assigned_users.append(user)
                
        # Назначаем пользователей по выбранным группам
        group_names = json.loads(data.get('group_names', '[]'))
        for group_name in group_names:
            users_in_group = User.query.filter_by(group=group_name).all()
            for user in users_in_group:
                if user not in template.assigned_users:
                    template.assigned_users.append(user)
                    
        # Назначаем уже существующие прикрепленные файлы
        from app.models import UploadedFile
        file_ids = json.loads(data.get('file_ids', '[]'))
        for f_id in file_ids:
            file_obj = UploadedFile.query.get(f_id)
            if file_obj and file_obj not in template.attachments:
                template.attachments.append(file_obj)
                
        # Загружаем НОВЫЕ файлы прямо из конструктора
        import os, uuid
        from werkzeug.utils import secure_filename
        from config import basedir
        from flask_login import current_user
        
        UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads', 'reports')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        from app.admin.routes_files import allowed_file, MAX_FILE_SIZE
        
        new_files = request.files.getlist('new_files')
        for file in new_files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    return jsonify({'status': 'error', 'message': f'Формат файла {file.filename} не поддерживается (разрешены pdf, docx, xlsx, doc, xls)'}), 400
                    
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                
                if size > MAX_FILE_SIZE:
                    return jsonify({'status': 'error', 'message': f'Файл {file.filename} превышает лимит в 50 МБ'}), 400

                original_name = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_name}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                file.save(file_path)
                
                new_file_obj = UploadedFile(
                    filename=file.filename,
                    filepath=unique_filename,
                    uploader_id=current_user.id,
                    file_size=size
                )
                db.session.add(new_file_obj)
                template.attachments.append(new_file_obj)
                
        db.session.commit()
        log_action('Создание отчета (Конструктор)', f'Создан новый шаблон отчета: {template.short_name}')
        return jsonify({'status': 'success'})
        
    # GET запрос - просто отдаем пустую страницу конструктора
    users = User.query.filter(User.role == 'user').all()
    
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']
        
    from app.models import UploadedFile, Dictionary
    all_files = UploadedFile.query.order_by(UploadedFile.upload_date.desc()).all()
    all_dictionaries = Dictionary.query.order_by(Dictionary.name).all()
        
    return render_template('constructor.html', users=users, all_groups=all_groups, all_files=all_files, all_dictionaries=all_dictionaries)

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
        import json
        data = request.form
        deadline_str = data.get('deadline')
        
        # Обновляем мета-информацию и структуру
        template.name = data.get('name')
        template.short_name = data.get('short_name')
        template.period = data.get('period')
        period_data_str = data.get('period_data')
        template.period_data = json.loads(period_data_str) if period_data_str else None
        template.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        template.schema = json.loads(data.get('schema', '[]'))
        
        # Полностью пересобираем список назначенных пользователей (удаляем старые, добавляем новые)
        template.assigned_users = []
        user_ids = json.loads(data.get('user_ids', '[]'))
        for u_id in user_ids:
            user = User.query.get(u_id)
            if user and user not in template.assigned_users:
                template.assigned_users.append(user)
                
        group_names = json.loads(data.get('group_names', '[]'))
        for group_name in group_names:
            users_in_group = User.query.filter_by(group=group_name).all()
            for user in users_in_group:
                if user not in template.assigned_users:
                    template.assigned_users.append(user)
                    
        # Полностью пересобираем список прикрепленных файлов
        template.attachments = []
        from app.models import UploadedFile
        file_ids = json.loads(data.get('file_ids', '[]'))
        for f_id in file_ids:
            file_obj = UploadedFile.query.get(f_id)
            if file_obj and file_obj not in template.attachments:
                template.attachments.append(file_obj)
                
        # Загружаем НОВЫЕ файлы прямо из конструктора
        import os, uuid
        from werkzeug.utils import secure_filename
        from config import basedir
        from flask_login import current_user
        
        UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads', 'reports')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        from app.admin.routes_files import allowed_file, MAX_FILE_SIZE
        
        new_files = request.files.getlist('new_files')
        for file in new_files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    return jsonify({'status': 'error', 'message': f'Формат файла {file.filename} не поддерживается (разрешены pdf, docx, xlsx, doc, xls)'}), 400
                    
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                
                if size > MAX_FILE_SIZE:
                    return jsonify({'status': 'error', 'message': f'Файл {file.filename} превышает лимит в 50 МБ'}), 400

                original_name = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_name}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                file.save(file_path)
                
                new_file_obj = UploadedFile(
                    filename=file.filename,
                    filepath=unique_filename,
                    uploader_id=current_user.id,
                    file_size=size
                )
                db.session.add(new_file_obj)
                template.attachments.append(new_file_obj)
                
        db.session.commit()
        log_action('Редактирование структуры отчета', f'Обновлена структура шаблона отчета: {template.short_name}')
        return jsonify({'status': 'success'})

    # GET запрос - загружаем форму и передаем в неё старый шаблон
    users = User.query.filter(User.role == 'user').all()
    
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']
        
    from app.models import UploadedFile, Dictionary
    all_files = UploadedFile.query.order_by(UploadedFile.upload_date.desc()).all()
    all_dictionaries = Dictionary.query.order_by(Dictionary.name).all()
        
    return render_template('constructor.html', users=users, template=template, all_groups=all_groups, all_files=all_files, all_dictionaries=all_dictionaries)

@admin_bp.route('/constructor/import_excel', methods=['POST'])
@login_required
def import_excel_template():
    """
    Маршрут умного парсинга Excel файлов.
    Принимает Excel файл, сканирует его листы, строит иерархическое дерево шапки
    и создает черновой ReportTemplate (шаблон).
    """
    try:
        import openpyxl
        import time
        from app.services.excel_parser import ExcelParser
        
        file = request.files.get('file')
        if not file or not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return jsonify({'status': 'error', 'message': 'Пожалуйста, загрузите файл .xlsx или .xls'}), 400

        # Обработка старого формата .xls (конвертация в .xlsx через xls2xlsx)
        if file.filename.endswith('.xls'):
            import tempfile
            import os
            from xls2xlsx import XLS2XLSX
            
            tf_xls = tempfile.NamedTemporaryFile(suffix='.xls', delete=False)
            tf_xls.close()
            temp_xls = tf_xls.name
            
            file.save(temp_xls)
            x2x = XLS2XLSX(temp_xls)
            
            tf_xlsx = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            tf_xlsx.close()
            temp_xlsx = tf_xlsx.name
                
            x2x.to_xlsx(temp_xlsx)
            wb = openpyxl.load_workbook(temp_xlsx, data_only=True)
            
            os.remove(temp_xls)
            os.remove(temp_xlsx)
        else:
            wb = openpyxl.load_workbook(file, data_only=True)

        # Вызываем новый сервис умного парсинга
        schema = ExcelParser.parse_workbook(wb)
        wb.close()
        
        if not schema:
            return jsonify({'status': 'error', 'message': 'Не удалось найти таблицы с заголовками в файле.'}), 400
            
        # Создаем черновой шаблон в БД
        original_filename = file.filename or "Новый шаблон"
        base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        if not base_name.strip():
            base_name = "Новый шаблон"
        
        template = ReportTemplate(
            name=base_name,
            short_name=base_name[:30],
            is_published=False,
            is_template=True,
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