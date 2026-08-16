from app import create_app
from app.models import ReportTemplate

app = create_app()
with app.app_context():
    templates = ReportTemplate.query.filter_by(is_template=False, is_published=True).all()
    for t in templates:
        schema = t.schema
        if schema:
            for sheet in schema:
                for field in sheet.get('fields', []):
                    if field.get('children'):
                        print(f"Template {t.id} -> field: {field.get('name')}")
                        if "Трудоустроены" in field.get('name', ''):
                            print("FOUND MATCH!")
