from app import create_app, db
from app.models import ReportTemplate
import json

app = create_app()
with app.app_context():
    t = ReportTemplate.query.order_by(ReportTemplate.id.desc()).first()
    if t:
        print(f"Template {t.id}: {t.name}")
        print(json.dumps(t.schema, indent=2, ensure_ascii=False))
