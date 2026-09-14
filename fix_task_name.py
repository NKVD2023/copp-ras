with open('/home/admin-copp/copp-ras/app/services/task_service.py', 'r') as f:
    content = f.read()

orig = 'name=f"Генерация отчета: {template.short_name}",'
new = 'name=f"Генерация отчета: {template.short_name}"[:128],'
content = content.replace(orig, new)

with open('/home/admin-copp/copp-ras/app/services/task_service.py', 'w') as f:
    f.write(content)
print("Fixed BackgroundTask name length")
