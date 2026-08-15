import json
import uuid
import time
import copy
from app import create_app, db
from app.models import ReportTemplate
from sqlalchemy.orm.attributes import flag_modified

def generate_field_name(sheet_idx, field_idx):
    timestamp = int(time.time() * 1000)
    return f"s{sheet_idx}_c{str(timestamp + field_idx)[-6:]}"

def patch_templates():
    app = create_app()
    with app.app_context():
        templates = ReportTemplate.query.all()
        fixed_count = 0
        
        for template in templates:
            if not template.schema:
                continue
                
            schema = copy.deepcopy(template.schema)
            if isinstance(schema, str):
                try:
                    schema = json.loads(schema)
                except:
                    continue
            
            seen_ids = set()
            changed = False
            
            for sIdx, sheet in enumerate(schema):
                fields = sheet.get("fields", [])
                for fIdx, field in enumerate(fields):
                    field_id = field.get("id") or field.get("name")
                    if not field_id:
                        continue
                        
                    if field_id in seen_ids:
                        new_id = generate_field_name(sIdx + 1, fIdx)
                        time.sleep(0.01)
                        while new_id in seen_ids:
                            new_id = generate_field_name(sIdx + 1, fIdx + 100)
                            time.sleep(0.01)
                            
                        field["name"] = new_id
                        field["id"] = new_id
                        seen_ids.add(new_id)
                        changed = True
                    else:
                        seen_ids.add(field_id)
                        
            if changed:
                template.schema = schema
                flag_modified(template, "schema")
                fixed_count += 1
                
        db.session.commit()
        print(f"✅ Successfully patched {fixed_count} templates.")

if __name__ == '__main__':
    patch_templates()
