import json
import re

def normalize_label(label):
    if not label: return ''
    return re.sub(r'\W+', '', str(label)).lower()

old_schema = [{'sheet_title': 'Информация о студентах', 'fields': [{'name': 's0_c587205', 'label': 'Наименование образовательной организации', 'type': 'text', 'required': False}, {'name': 's0_c598409', 'label': 'Всего студентов ПОО, в отношении которых проведена оценка риска нетрудоустройства, чел.', 'type': 'number', 'required': False}, {'name': 's0_c622360', 'label': 'Всего студентов ПОО, охваченных профориентационными мероприятиями образовательных организаций,  чел', 'type': 'number', 'required': False}, {'name': 's0_c815213', 'label': 'Всего студентов ВО, в отношении которых проведена оценка риска нетрудоустройства, чел.', 'type': 'number', 'required': False}, {'name': 's0_c838366', 'label': 'Всего студентов ВО, охваченных профориентационными мероприятиями образовательных организаций, чел', 'type': 'number', 'required': False}]}]

new_schema = [{'sheet_title': 'Информация о студентах', 'fields': [{'name': 's0_c876412', 'label': 'Всего студентов ПОО, в отношении которых проведена оценка риска нетрудоустройства, чел', 'type': 'number', 'required': True, 'is_multiple': False, 'hint': ''}, {'name': 's0_c883810', 'label': 'Всего студентов ПОО, охваченных профориентационными мероприятиями образовательных организаций, чел', 'type': 'number', 'required': True, 'is_multiple': False, 'hint': ''}, {'name': 's0_c891724', 'label': 'Всего студентов ВО, в отношении которых проведена оценка риска нетрудоустройства, чел.', 'type': 'number', 'required': True, 'is_multiple': False, 'hint': ''}, {'name': 's0_c898619', 'label': 'Всего студентов ВО, охваченных профориентационными мероприятиями образовательных организаций, чел', 'type': 'number', 'required': True, 'is_multiple': False, 'hint': ''}]}]

old_data = {
   "s0_c587205": "МГУ",
   "s0_c598409": "100",
   "s0_c622360": "50",
   "s0_c815213": "20",
   "s0_c838366": "10"
}

# 1. Map old name to normalized label
old_name_to_norm_label = {}
if old_schema:
    for sheet in old_schema:
        for field in sheet.get('fields', []):
            old_name_to_norm_label[field['name']] = normalize_label(field.get('label', ''))

# 2. Map normalized label to new name
norm_label_to_new_name = {}
if new_schema:
    for sheet in new_schema:
        for field in sheet.get('fields', []):
            norm_label_to_new_name[normalize_label(field.get('label', ''))] = field['name']

# 3. Translate data
new_data = {}
for old_name, value in old_data.items():
    if old_name in old_name_to_norm_label:
        norm_label = old_name_to_norm_label[old_name]
        if norm_label in norm_label_to_new_name:
            new_name = norm_label_to_new_name[norm_label]
            new_data[new_name] = value
    else:
        # If it wasn't in schema (e.g. some meta field?), just copy it maybe?
        # Actually, let's keep it just in case
        new_data[old_name] = value

print(json.dumps(new_data, indent=2))
