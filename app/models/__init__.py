"""
app/models/__init__.py
Реэкспортирует все модели для обратной совместимости.
Весь остальной код проекта продолжает делать: from app.models import User
"""
from app.models.user import User, user_template_access
from app.models.files import UploadedFile, report_attachments
from app.models.report import ReportTemplate, ReportSubmission, ReportDraft
from app.models.logs import ActionLog
from app.models.tasks import BackgroundTask
from app.models.dictionaries import Dictionary

__all__ = [
    'User', 'user_template_access',
    'UploadedFile', 'report_attachments',
    'ReportTemplate', 'ReportSubmission', 'ReportDraft',
    'ActionLog', 'BackgroundTask', 'Dictionary',
]
