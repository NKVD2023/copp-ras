"""
app/models/__init__.py
Реэкспортирует все модели для обратной совместимости.
Весь остальной код проекта продолжает делать: from app.models import User
"""
from app.models.user import User, user_template_access
from app.models.report import ReportTemplate, ReportSubmission, ReportDraft, report_attachments
from app.models.files import UploadedFile
from app.models.logs import ActionLog
from app.models.tasks import BackgroundTask
from app.models.dictionaries import Dictionary
from app.models.department import Department, department_templates

__all__ = [
    'User',
    'user_template_access',
    'ReportTemplate',
    'ReportSubmission',
    'ReportDraft',
    'report_attachments',
    'UploadedFile',
    'ActionLog',
    'BackgroundTask',
    'Dictionary',
    'Department',
    'department_templates',
]
