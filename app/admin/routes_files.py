import os
import uuid
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin import admin_bp
from app.models import UploadedFile, ReportTemplate
from config import basedir

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx'}
MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB
UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads', 'reports')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('Нет файла для загрузки', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    uploaded_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            if size > MAX_FILE_SIZE:
                flash(f'Файл {file.filename} превышает лимит в 50 МБ', 'danger')
                continue
                
            original_name = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_name}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            try:
                file.save(file_path)
                
                new_file = UploadedFile(
                    filename=file.filename,
                    filepath=unique_filename,
                    uploader_id=current_user.id,
                    file_size=size
                )
                db.session.add(new_file)
                uploaded_count += 1
            except Exception as e:
                flash(f'Ошибка при сохранении {file.filename}: {e}', 'danger')
        else:
            flash(f'Формат файла {file.filename} не поддерживается', 'danger')
            
    if request.args.get('ajax') == '1':
        db.session.commit()
        # We need to query the last inserted files for the current user, or just return success
        # Actually it's easier to just return success and let the frontend reload or we just return the new files.
        # But we don't have new_files_list. Let's just return success for now.
        return {'status': 'success'}

    if uploaded_count > 0:
        db.session.commit()
        from app.utils import log_action
        log_action('Загрузка файлов', f'Загружено {uploaded_count} файлов')
        flash(f'Успешно загружено файлов: {uploaded_count}', 'success')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    file_obj = UploadedFile.query.get_or_404(file_id)
    
    # Check if attached to any reports
    if file_obj.reports.count() > 0:
        flash(f'Файл "{file_obj.filename}" прикреплен к отчетам и не может быть удален. Сначала открепите его.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file_obj.filepath)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        db.session.delete(file_obj)
        db.session.commit()
        
        from app.utils import log_action
        log_action('Удаление файла', f'Удален файл {file_obj.filename}')
        flash('Файл успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {e}', 'danger')
        
    return redirect(url_for('admin.dashboard'))
