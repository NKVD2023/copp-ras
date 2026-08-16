import json
from app import create_app
from app.models import ReportTemplate
from app.services.stat_service import StatService

app = create_app()
with app.app_context():
    t = ReportTemplate.query.filter_by(is_template=False, is_published=True).order_by(ReportTemplate.id.desc()).first()
    schema = StatService.build_unified_stat_schema([t], 2)
    print(json.dumps(schema[0]['header_rows'], ensure_ascii=False, indent=2))
