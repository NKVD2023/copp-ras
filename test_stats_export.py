from app import create_app
from app.services.excel_service import ExcelService
from app.services.stat_service import StatService
from app.models import ReportTemplate
import sys

app = create_app()
with app.app_context():
    try:
        # User ID 2 is likely test user based on previous work
        templates = ReportTemplate.query.filter_by(short_name="СПО-1", is_template=False, is_published=True).order_by(ReportTemplate.id.desc()).all()
        if templates:
            stat_schema = StatService.build_unified_stat_schema(templates, 2)
            if stat_schema:
                ExcelService.export_statistics(stat_schema, "Test", user_title="Test User")
                print("Export successful!")
            else:
                print("No stats generated")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
