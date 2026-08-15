from app import create_app, db
from app.models import ReportTemplate
import json

app = create_app()
with app.app_context():
    template = ReportTemplate.query.order_by(ReportTemplate.id.desc()).first()
    schema = template.schema
    if isinstance(schema, str):
        schema = json.loads(schema)
    
    print(f"Template ID: {template.id}")
    for s_idx, sheet in enumerate(schema):
        print(f"Sheet {s_idx}: {sheet.get('sheet_title')}")
        for f in sheet.get('fields', [])[:2]:
            print(f"  Field: {f.get('name')}")
