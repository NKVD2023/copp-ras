import json
from app import create_app
from app.extensions import db
from app.models import ReportTemplate
from sqlalchemy.orm.attributes import flag_modified

app = create_app()
with app.app_context():
    templates = ReportTemplate.query.all()
    repaired_count = 0
    for t in templates:
        if not t.schema:
            continue
            
        modified = False
        schema_data = t.schema
        if isinstance(schema_data, str):
            try:
                schema_data = json.loads(schema_data)
            except:
                continue
                
        for sheet in schema_data:
            for field in sheet.get('fields', []):
                # 1. Fix missing name
                if not field.get('name'):
                    field_id = field.get('id')
                    if field_id:
                        field['name'] = field_id
                        modified = True
                        # 2. Since it had no name, it was forcibly deactivated by the bug.
                        # Restore is_active = True
                        if field.get('is_active') is False:
                            field['is_active'] = True
                            print(f"Restoring field {field_id} in template {t.id} ({t.name})")

        if modified:
            t.schema = schema_data
            flag_modified(t, 'schema')
            repaired_count += 1
            
    db.session.commit()
    print(f"Repaired {repaired_count} templates.")
