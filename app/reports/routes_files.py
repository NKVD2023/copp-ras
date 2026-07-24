import os
from flask import send_from_directory, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from app.reports import reports_bp
from app.models import UploadedFile
from config import basedir

UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads', 'reports')

@reports_bp.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    file_obj = UploadedFile.query.get_or_404(file_id)
    
    # Check permissions
    if current_user.role not in ['admin', 'viewer']:
        # Regular user: check if file is attached to any report assigned to them
        has_access = False
        for report in file_obj.reports:
            if current_user in report.assigned_users:
                has_access = True
                break
        
        if not has_access:
            flash('У вас нет доступа к этому файлу.', 'danger')
            return redirect(url_for('reports.dashboard'))
            
    # File is accessible
    file_path = os.path.join(UPLOAD_FOLDER, file_obj.filepath)
    if not os.path.exists(file_path):
        flash('Файл не найден на сервере.', 'danger')
        return redirect(url_for('reports.dashboard'))
        
    return send_from_directory(
        directory=UPLOAD_FOLDER,
        path=file_obj.filepath,
        as_attachment=True,
        download_name=file_obj.filename
    )
