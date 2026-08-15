from app import create_app, db
from app.models import ReportTemplate, ReportSubmission
from app.services.excel_service import ExcelService
import sys

app = create_app()
with app.app_context():
    template = ReportTemplate.query.order_by(ReportTemplate.id.desc()).first()
    submissions = ReportSubmission.query.filter_by(template_id=template.id).all()
    try:
        output, filename = ExcelService.export_debtors(template, []) # actually we should use export_report
    except AttributeError:
        pass
        
    try:
        output, filename = ExcelService.export_report(template, submissions)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
