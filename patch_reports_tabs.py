import re

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove "Мои отчеты" heading (lines 6-27)
header_pattern = r'<div class="row mb-4 align-items-center">.*?<h3 class="fw-bold text-dark m-0">Мои отчеты</h3>.*?</div>\s*</div>\s*</div>'
content = re.sub(header_pattern, '', content, flags=re.DOTALL)

# 2. Remove old nav-tabs (lines 51-71 approx)
nav_pattern = r'<ul class="nav nav-tabs mb-4" id="userTabs" role="tablist">.*?</ul>'
content = re.sub(nav_pattern, '', content, flags=re.DOTALL)

# 3. Fix col-md-4 to col-md-6 col-lg-4 col-xl-4
content = content.replace('class="col-md-4 user-report-item"', 'class="col-md-6 col-lg-4 col-xl-4 user-report-item"')
content = content.replace('class="col-md-4 user-report-item "', 'class="col-md-6 col-lg-4 col-xl-4 user-report-item "')

# 4. Add draft badge and files badge logic (we will inject it after the calendar badge)
badge_injection = """<span class="badge bg-white text-dark border"><i class="bi bi-calendar"></i> Период: {{ template.period or 'не указан' }}</span>
                                {% if template.attachments|length > 0 %}
                                <span class="badge bg-secondary border"><i class="bi bi-paperclip"></i> Файлов: {{ template.attachments|length }}</span>
                                {% endif %}
                                <span class="badge bg-info text-dark border d-none draft-badge" data-template-id="{{ template.id }}"><i class="bi bi-cloud-check"></i> Есть черновик</span>"""

content = content.replace('<span class="badge bg-white text-dark border"><i class="bi bi-calendar"></i> Период: {{ template.period or \'не указан\' }}</span>', badge_injection)

# 5. Fix the overdueTab duplication (which was in the old code anyway? Let's check if the old code had duplication)
# In the original file, overdueTab has this structure. If the original had it, it will still be there.
# Let's clean up the whole overdueTab and unfilledTab loop if needed, but wait, did the original have duplication?
# Let's save and then we can check.

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
