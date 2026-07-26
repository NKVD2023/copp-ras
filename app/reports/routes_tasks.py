from flask import jsonify, send_file
from flask_login import login_required
from app.reports import reports_bp
from app.models import BackgroundTask
import os

@reports_bp.route('/task_status/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    task = BackgroundTask.query.get_or_404(task_id)
    response = {
        'status': task.status,
        'name': task.name
    }
    if task.status == 'SUCCESS':
        response['message'] = 'Task completed successfully'
    elif task.status == 'FAILED':
        response['message'] = task.error_message or 'Task failed'
        
    return jsonify(response)

@reports_bp.route('/task_download/<task_id>', methods=['GET'])
@login_required
def download_task_result(task_id):
    task = BackgroundTask.query.get_or_404(task_id)
    if task.status != 'SUCCESS' or not task.result_path:
        return "Файл еще не готов или произошла ошибка", 400
        
    if not os.path.exists(task.result_path):
        return "Файл не найден", 404
        
    # Get the original filename without the unique id prefix if possible, or just send it
    filename = os.path.basename(task.result_path)
    
    # Remove the UUID prefix that was added for uniqueness
    prefix = f"{task.id}_"
    if filename.startswith(prefix):
        filename = filename[len(prefix):]
        
    # The actual downloading
    return send_file(task.result_path, as_attachment=True, download_name=filename)
