import threading
import uuid
from app import db
from app.models import BackgroundTask, ReportTemplate, ReportSubmission
from app.services.excel_service import ExcelService
import os

class TaskService:
    @staticmethod
    def _generate_excel_thread(task_id, template_id, app, save_dir):
        # We need a new application context for the background thread
        with app.app_context():
            task = BackgroundTask.query.get(task_id)
            if not task:
                return
                
            try:
                template = ReportTemplate.query.get(template_id)
                submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
                
                # Use ExcelService to generate output
                output, filename = ExcelService.export_report(template, submissions)
                
                # Save to disk (save_dir передаётся явно, чтобы избежать неправильного root_path в потоке)
                os.makedirs(save_dir, exist_ok=True)
                
                # Prepend task_id to ensure uniqueness
                unique_filename = f"{task_id}_{filename}"
                filepath = os.path.join(save_dir, unique_filename)
                
                with open(filepath, 'wb') as f:
                    f.write(output.read())
                    
                task.status = 'SUCCESS'
                task.result_path = filepath
                
            except Exception as e:
                task.status = 'FAILED'
                task.error_message = str(e)
                
            db.session.commit()

    @staticmethod
    def start_excel_generation(template_id, current_user_id):
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        template = ReportTemplate.query.get_or_404(template_id)
        
        # Create task record
        task = BackgroundTask(
            id=task_id,
            name=f"Генерация отчета: {template.short_name}",
            user_id=current_user_id
        )
        db.session.add(task)
        db.session.commit()
        
        # Start background thread
        from flask import current_app
        app = current_app._get_current_object()
        
        # Вычисляем путь здесь, в контексте запроса, где root_path точно правильный
        save_dir = os.path.join(app.root_path, 'static', 'uploads', 'tasks')
        
        thread = threading.Thread(
            target=TaskService._generate_excel_thread,
            args=(task_id, template_id, app, save_dir)
        )
        thread.start()
        
        return task_id
