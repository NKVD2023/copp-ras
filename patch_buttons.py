import re

with open('/home/copp-admin/copp-ras/app/templates/fill_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace bottom buttons
old_buttons = """                <div class="d-flex gap-2 flex-wrap justify-content-end w-100 mt-2">
                    <a href="{{ url_for('reports.dashboard') }}" class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2 me-auto">
                        <i class="bi bi-arrow-left"></i> Назад
                    </a>
                    <button type="button" onclick="loadPreviousData()" class="btn btn-outline-secondary px-3 py-2 d-flex align-items-center gap-2" id="btn-no-changes">
                        <i class="bi bi-clock-history"></i> Из прошлого
                    </button>
                    <button type="button" onclick="saveDraftManual(this)" class="btn btn-outline-primary px-4 py-2 d-flex align-items-center gap-2">
                        <i class="bi bi-save"></i> Сохранить черновик
                    </button>
                    <button type="button" onclick="submitFullForm(this)" class="btn btn-copp px-5 py-2 d-flex align-items-center gap-2">
                        <i class="bi bi-check2"></i> Сдать отчет
                    </button>
                </div>"""

new_buttons = """                <div class="d-flex gap-2 flex-wrap justify-content-end w-100 mt-2">
                    <a href="{{ url_for('reports.dashboard') }}" class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2 me-auto">
                        <i class="bi bi-arrow-left"></i> Назад
                    </a>
                    <button type="button" onclick="loadPreviousData()" class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2" id="btn-no-changes">
                        <i class="bi bi-clock-history text-secondary"></i> Без изменений
                    </button>
                    <button type="button" onclick="saveDraftManual(this)" class="btn btn-light border px-4 py-2 d-flex align-items-center gap-2 text-primary">
                        <i class="bi bi-save"></i> Сохранить черновик
                    </button>
                    <button type="button" onclick="submitFullForm(this)" class="btn btn-copp px-5 py-2 d-flex align-items-center gap-2">
                        <i class="bi bi-check2"></i> Сдать отчет
                    </button>
                </div>"""

content = content.replace(old_buttons, new_buttons)

# Add top back button
# Let's find a good place for it. Maybe right above the form card, inside main container.
# Currently it starts with <div class="container main-container mt-4 mb-5">
# Let's add it right after that line.
top_back_html = """
    <div class="mb-3">
        <a href="{{ url_for('reports.dashboard') }}" class="btn btn-light border px-3 py-1 d-inline-flex align-items-center gap-2 text-muted small hoverable">
            <i class="bi bi-arrow-left"></i> Вернуться к списку отчетов
        </a>
    </div>"""

# Ensure we don't add it twice
if "Вернуться к списку отчетов" not in content:
    content = content.replace('<div class="container main-container mt-4 mb-5">', '<div class="container main-container mt-4 mb-5">' + top_back_html)

with open('/home/copp-admin/copp-ras/app/templates/fill_report.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
