import json
import uuid
import time
from app import create_app, db
from app.models import ReportTemplate

def generate_field_name(sheet_idx, field_idx):
    timestamp = int(time.time() * 1000)
    return f"s{sheet_idx}_c{str(timestamp + field_idx)[-6:]}"

app = create_app()
with app.app_context():
    templates = ReportTemplate.query.all()
    patched_count = 0
    
    for template in templates:
        schema = template.schema
        if not schema or not isinstance(schema, list):
            continue
            
        modified = False
        seen_fields = set()
        
        for s_idx, sheet in enumerate(schema):
            fields = sheet.get("fields", [])
            for f_idx, field in enumerate(fields):
                f_id = field.get("id")
                f_name = field.get("name")
                
                # Check for duplicates across the entire template
                if f_id in seen_fields or f_name in seen_fields:
                    new_id = generate_field_name(s_idx, f_idx)
                    field["id"] = new_id
                    field["name"] = new_id
                    modified = True
                    seen_fields.add(new_id)
                else:
                    if f_id: seen_fields.add(f_id)
                    if f_name: seen_fields.add(f_name)
                    
        if modified:
            template.schema = schema
            # SQLAlchemy JSON mutation tracking might need this:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(template, "schema")
            patched_count += 1
            
    db.session.commit()
    print(f"Patched {patched_count} templates successfully.")
