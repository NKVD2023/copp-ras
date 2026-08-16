"""
Модуль администратора: Управление Базой Данных (Admin - Database).
Позволяет напрямую редактировать записи в БД (с проверкой пароля),
создавать резервные копии SQLite файла, скачивать их, удалять и восстанавливать.
"""
from flask import request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission
from app import db
from datetime import datetime
import os
import shutil
import zipfile
import io
import tempfile
from config import basedir
from app.utils import log_action
from app.auth.decorators import roles_required

@admin_bp.route('/db_update', methods=['POST'])
@login_required
@roles_required('admin')
def db_update():
    """
    Массовое или одиночное обновление полей напрямую в базе данных.
    Используется во вкладке "База данных" администратора.
    Требует обязательного подтверждения паролем администратора (в заголовках запроса).
    """
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
    # Проверка пароля администратора перед внесением изменений
    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401
        
    updates = request.get_json()
    if not isinstance(updates, list):
        updates = [updates]
        
    model_map = {
        'User': User,
        'ReportTemplate': ReportTemplate,
        'ReportSubmission': ReportSubmission
    }
    
    # Жесткий белый список полей, которые разрешено редактировать напрямую
    ALLOWED_UPDATE_FIELDS = {
        'User': ['username', 'description'],
        'ReportTemplate': ['name', 'short_name', 'period', 'deadline', 'is_published'],
        'ReportSubmission': ['data']
    }
    
    for item in updates:
        model_name = item.get('model')
        row_id = item.get('id')
        field = item.get('field')
        value = item.get('value')
        
        if not all([model_name, row_id, field]):
            continue
            
        # Защита от изменения критических полей (например пароля или роли)
        if model_name not in ALLOWED_UPDATE_FIELDS or field not in ALLOWED_UPDATE_FIELDS[model_name]:
            return jsonify({'status': 'error', 'message': f'Поле {field} запрещено для изменения напрямую'}), 403
            
        ModelClass = model_map.get(model_name)
        if not ModelClass:
            continue
            
        record = ModelClass.query.get(row_id)
        if record and hasattr(record, field):
            # Конвертация типов для некоторых специфичных полей
            if field == 'is_published':
                value = str(value).lower() in ['true', '1', 'yes', 'да']
            elif field == 'deadline':
                try:
                    value = datetime.strptime(value, '%Y-%m-%d').date() if value else None
                except ValueError:
                    continue # Игнорируем неверный формат даты
            
            setattr(record, field, value)
            
    try:
        db.session.commit()
        log_action('Редактирование БД', f'Внесены прямые изменения в базу данных ({len(updates)} записей)')
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

# ==========================================
# РЕЗЕРВНОЕ КОПИРОВАНИЕ (BACKUPS)
# ==========================================

@admin_bp.route('/db/backup/create', methods=['POST'])
@login_required
@roles_required('admin')
def create_backup():
    """
    Создает физическую резервную копию файла базы данных SQLite (reports.db)
    в директорию /backups. Требует подтверждения паролем.
    """
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401
        
    backups_dir = os.path.join(basedir, 'backups')
    db_path = os.path.join(basedir, 'reports.db')
    
    if not os.path.exists(db_path):
        return jsonify({'status': 'error', 'message': 'Файл БД не найден'}), 404
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}.db'
    backup_path = os.path.join(backups_dir, backup_name)
    
    try:
        shutil.copy2(db_path, backup_path)
        log_action('Бэкап БД', f'Создана резервная копия {backup_name}')
        return jsonify({'status': 'success', 'message': 'Резервная копия создана'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@admin_bp.route('/db/backup/download_current')
@login_required
@roles_required('admin')
def download_current_db():
    """Скачивание текущего (рабочего) файла базы данных и папки uploads в виде ZIP-архива."""
    if current_user.role != 'admin':
        return "Forbidden", 403
        
    db_path = os.path.join(basedir, 'reports.db')
    uploads_dir = os.path.join(basedir, 'app', 'uploads')
    
    if not os.path.exists(db_path):
        return "Database file not found", 404

    # Создаем ZIP в памяти
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Добавляем БД
        zf.write(db_path, 'reports.db')
        
        # Добавляем загруженные файлы (если есть)
        if os.path.exists(uploads_dir):
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Вычисляем относительный путь для архива (например, app/uploads/image.png)
                    rel_path = os.path.relpath(file_path, basedir)
                    zf.write(file_path, rel_path)
                    
    memory_file.seek(0)
    
    log_action('Скачивание полного бэкапа', 'Скачана текущая база данных и загруженные файлы')
    
    filename = f'copp_backup_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    return send_file(memory_file, as_attachment=True, download_name=filename, mimetype='application/zip')

@admin_bp.route('/db/backup/download/<filename>')
@login_required
@roles_required('admin')
def download_backup(filename):
    """Скачивание конкретной исторической резервной копии из папки /backups."""
    if current_user.role != 'admin':
        return "Forbidden", 403

    # Защита от Path Traversal: проверяем, что итоговый путь остается внутри backups/
    backups_dir = os.path.realpath(os.path.join(basedir, 'backups'))
    backup_path = os.path.realpath(os.path.join(backups_dir, filename))
    if not backup_path.startswith(backups_dir + os.sep):
        return "Доступ запрещён", 403

    if os.path.exists(backup_path):
        log_action('Скачивание БД', f'Скачана резервная копия {filename}')
        return send_file(backup_path, as_attachment=True)
    return "File not found", 404

@admin_bp.route('/db/backup/delete/<filename>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_backup(filename):
    """Удаление резервной копии из папки /backups."""
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403

    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401

    # Защита от Path Traversal
    backups_dir = os.path.realpath(os.path.join(basedir, 'backups'))
    backup_path = os.path.realpath(os.path.join(backups_dir, filename))
    if not backup_path.startswith(backups_dir + os.sep):
        return jsonify({'status': 'error', 'message': 'Доступ запрещён'}), 403

    if os.path.exists(backup_path):
        os.remove(backup_path)
        log_action('Удаление бэкапа БД', f'Удалена резервная копия {filename}')
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404

@admin_bp.route('/db/backup/restore/<filename>', methods=['POST'])
@login_required
@roles_required('admin')
def restore_backup(filename):
    """
    Восстановление базы данных из старого бэкапа.
    Перезаписывает рабочий reports.db файлом из папки /backups.
    """
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403

    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401

    # Защита от Path Traversal
    backups_dir = os.path.realpath(os.path.join(basedir, 'backups'))
    backup_path = os.path.realpath(os.path.join(backups_dir, filename))
    if not backup_path.startswith(backups_dir + os.sep):
        return jsonify({'status': 'error', 'message': 'Доступ запрещён'}), 403

    db_path = os.path.join(basedir, 'reports.db')

    if not os.path.exists(backup_path):
        return jsonify({'status': 'error', 'message': 'Бэкап не найден'}), 404

    try:
        # Сначала закрываем текущую сессию, чтобы её кэшированные данные не перезаписали новый файл при коммите лога
        db.session.remove()
        # Сброс пула подключений к БД (важно для Windows, чтобы снять лок с файла)
        db.engine.dispose()
        shutil.copy2(backup_path, db_path)
        log_action('Восстановление БД', f'База данных восстановлена из файла {filename}')
        return jsonify({'status': 'success', 'message': 'База данных успешно восстановлена'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@admin_bp.route('/db/backup/upload', methods=['POST'])
@login_required
@roles_required('admin')
def upload_backup():
    """
    Загрузка пользовательского ZIP-архива на сервер.
    Позволяет администратору восстановить базу и загруженные файлы.
    """
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    password = request.form.get('password')
    if not password or not current_user.check_password(password):
        flash('Неверный пароль')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    file = request.files.get('backup_file')
    if not file or not file.filename.endswith('.zip'):
        flash('Неверный формат файла. Требуется .zip')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    # Проверка на ZIP
    if not zipfile.is_zipfile(file):
        flash('Неверный формат архива. Это не ZIP.')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    db_path = os.path.join(basedir, 'reports.db')
    uploads_dir = os.path.join(basedir, 'app', 'uploads')
    
    try:
        # Распаковываем ZIP во временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            file.seek(0)
            with zipfile.ZipFile(file, 'r') as zf:
                zf.extractall(temp_dir)
                
            temp_db_path = os.path.join(temp_dir, 'reports.db')
            
            # Проверяем наличие reports.db в архиве
            if not os.path.exists(temp_db_path):
                flash('Ошибка: В архиве отсутствует reports.db')
                return redirect(url_for('admin.dashboard') + '#databaseTab')
                
            # Проверка сигнатуры SQLite
            with open(temp_db_path, 'rb') as f:
                header = f.read(16)
                if header != b'SQLite format 3\000':
                    flash('Ошибка: reports.db в архиве поврежден или не является базой SQLite.')
                    return redirect(url_for('admin.dashboard') + '#databaseTab')

            # Закрываем сессию и отпускаем БД
            db.session.remove()
            db.engine.dispose()
            
            # Перемещаем базу данных
            shutil.copy2(temp_db_path, db_path)
            
            # Восстанавливаем папку uploads (если она есть в архиве)
            # В архиве папка может называться app/uploads. Но из-за особенностей os.walk
            # файлы могли быть упакованы как 'app/uploads/file'
            temp_uploads_dir = os.path.join(temp_dir, 'app', 'uploads')
            
            if os.path.exists(temp_uploads_dir):
                # Бэкапим старую папку
                if os.path.exists(uploads_dir):
                    backup_uploads = os.path.join(basedir, 'app', 'uploads_bak')
                    if os.path.exists(backup_uploads):
                        shutil.rmtree(backup_uploads)
                    shutil.move(uploads_dir, backup_uploads)
                
                # Копируем новую
                shutil.copytree(temp_uploads_dir, uploads_dir)

            log_action('Восстановление полного бэкапа', f'Система восстановлена из архива {file.filename}')
            flash('Система (БД и файлы) успешно восстановлена из загруженного архива')
            
    except Exception as e:
        flash(f'Ошибка при восстановлении: {str(e)}')
        
    return redirect(url_for('admin.dashboard') + '#databaseTab')
