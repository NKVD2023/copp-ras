from flask import request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission
from app import db
from datetime import datetime
import os
import shutil
from config import basedir
from app.utils import log_action

@admin_bp.route('/db_update', methods=['POST'])
@login_required
def db_update():
    """Массовое обновление полей напрямую в базе данных."""
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
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
    
    for item in updates:
        model_name = item.get('model')
        row_id = item.get('id')
        field = item.get('field')
        value = item.get('value')
        
        if not all([model_name, row_id, field]):
            continue
            
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
# РЕЗЕРВНОЕ КОПИРОВАНИЕ
# ==========================================

@admin_bp.route('/db/backup/create', methods=['POST'])
@login_required
def create_backup():
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
def download_current_db():
    if current_user.role != 'admin':
        return "Forbidden", 403
        
    db_path = os.path.join(basedir, 'reports.db')
    if os.path.exists(db_path):
        log_action('Скачивание БД', 'Скачана текущая база данных')
        return send_file(db_path, as_attachment=True, download_name=f'copp_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    return "File not found", 404

@admin_bp.route('/db/backup/download/<filename>')
@login_required
def download_backup(filename):
    if current_user.role != 'admin':
        return "Forbidden", 403
        
    backup_path = os.path.join(basedir, 'backups', filename)
    if os.path.exists(backup_path):
        log_action('Скачивание БД', f'Скачана резервная копия {filename}')
        return send_file(backup_path, as_attachment=True)
    return "File not found", 404

@admin_bp.route('/db/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401
        
    backup_path = os.path.join(basedir, 'backups', filename)
    if os.path.exists(backup_path):
        os.remove(backup_path)
        log_action('Удаление бэкапа БД', f'Удалена резервная копия {filename}')
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404

@admin_bp.route('/db/backup/restore/<filename>', methods=['POST'])
@login_required
def restore_backup(filename):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
    password = request.headers.get('X-User-Password')
    if not password or not current_user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401
        
    backup_path = os.path.join(basedir, 'backups', filename)
    db_path = os.path.join(basedir, 'reports.db')
    
    if not os.path.exists(backup_path):
        return jsonify({'status': 'error', 'message': 'Бэкап не найден'}), 404
        
    try:
        # Сброс пула подключений, чтобы разблокировать файл (особенно актуально для Windows)
        db.engine.dispose()
        shutil.copy2(backup_path, db_path)
        log_action('Восстановление БД', f'База данных восстановлена из файла {filename}')
        return jsonify({'status': 'success', 'message': 'База данных успешно восстановлена'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@admin_bp.route('/db/backup/upload', methods=['POST'])
@login_required
def upload_backup():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    password = request.form.get('password')
    if not password or not current_user.check_password(password):
        flash('Неверный пароль')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    file = request.files.get('backup_file')
    if not file or not file.filename.endswith('.db'):
        flash('Неверный формат файла. Требуется .db')
        return redirect(url_for('admin.dashboard') + '#databaseTab')
        
    db_path = os.path.join(basedir, 'reports.db')
    try:
        db.engine.dispose()
        file.save(db_path)
        log_action('Восстановление БД', f'База данных восстановлена из загруженного файла {file.filename}')
        flash('База данных успешно восстановлена из загруженного файла')
    except Exception as e:
        flash(f'Ошибка при восстановлении: {str(e)}')
        
    return redirect(url_for('admin.dashboard') + '#databaseTab')
