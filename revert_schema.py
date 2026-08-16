import json
from app import create_app
from app.models import ReportTemplate
from app import db

app = create_app()
with app.app_context():
    templates = ReportTemplate.query.filter_by(is_template=False, is_published=True).all()
    for t in templates:
        schema = t.schema
        updated = False
        if schema:
            for sheet in schema:
                for field in sheet.get('fields', []):
                    if "Трудоустроены" in field.get('label', ''):
                        if 'validateSum' in field:
                            del field['validateSum']
                            updated = True
                            print(f"Reverted validateSum for field {field.get('name')} in template {t.id}")
        if updated:
            t.schema = schema
            db.session.commit()
            print(f"Reverted changes for template {t.id}")
