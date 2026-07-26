import re

with open('/home/copp-admin/copp-ras/app/templates/fill_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace light buttons with outline-copp
content = content.replace('class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2" id="btn-no-changes"', 'class="btn btn-outline-copp px-4 py-2 d-flex align-items-center gap-2" id="btn-no-changes"')
content = content.replace('class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2 text-primary"', 'class="btn btn-outline-copp px-4 py-2 d-flex align-items-center gap-2"')
content = content.replace('btn.classList.replace(\'btn-success\', \'btn-outline-primary\');', 'btn.classList.replace(\'btn-success\', \'btn-outline-copp\');')
content = content.replace('btn.classList.replace(\'btn-outline-primary\', \'btn-success\');', 'btn.classList.replace(\'btn-outline-copp\', \'btn-success\');')

with open('/home/copp-admin/copp-ras/app/templates/fill_report.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
