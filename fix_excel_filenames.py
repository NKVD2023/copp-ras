import re

def safe_filename(prefix, base_name, ext, max_base_len=50):
    """
    Safely truncates the base_name so the resulting filename is not too long.
    Replaces spaces with underscores and removes special characters.
    """
    safe_base = re.sub(r'[^\w\s-]', '', base_name).strip()
    safe_base = safe_base.replace(" ", "_")
    # Truncate base_name to max_base_len characters to avoid OSError: [Errno 36] File name too long
    # (Since Cyrillic chars take 2 bytes, 50 chars = 100 bytes, which leaves plenty of room for UUIDs)
    if len(safe_base) > max_base_len:
        safe_base = safe_base[:max_base_len] + "..."
    return f"{prefix}_{safe_base}{ext}"

with open('/home/admin-copp/copp-ras/app/services/excel_service.py', 'r') as f:
    content = f.read()

# Fix export_debtors
orig_debtors = 'filename = f"Должники_{template.short_name}.xlsx".replace(" ", "_")'
new_debtors = '''import re
        safe_name = re.sub(r'[^\\w\\s-]', '', template.short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"Должники_{safe_name}.xlsx"'''
content = content.replace(orig_debtors, new_debtors)

# Fix export_statistics
orig_stat = '''safe_name = short_name.replace(" ", "_").replace("/", "-")
        filename = f"Статистика_{safe_name}.xlsx"'''
new_stat = '''safe_name = re.sub(r'[^\\w\\s-]', '', short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"Статистика_{safe_name}.xlsx"'''
content = content.replace(orig_stat, new_stat)

# Fix export_report
orig_report = 'filename = f"Свод_{template.short_name}.xlsx".replace(" ", "_")'
new_report = '''safe_name = re.sub(r'[^\\w\\s-]', '', template.short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"Свод_{safe_name}.xlsx"'''
content = content.replace(orig_report, new_report)

with open('/home/admin-copp/copp-ras/app/services/excel_service.py', 'w') as f:
    f.write(content)
print("Fixed ExcelService filenames")
