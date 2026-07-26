with open("app/templates/constructor.html", "r") as f:
    content = f.read()

# 1. Hide the user checkboxes list by adding d-none
content = content.replace(
    '''<div class="row px-2">
                {% for user in users %}''',
    '''<div class="row px-2 d-none">
                {% for user in users %}'''
)

# 2. Modify the file selection UI
old_files_html = '''<label class="form-label small fw-bold text-dark mb-3">Прикрепленные файлы (инструкции, бланки, письма):</label>
            <div class="row px-2">
                {% for f in all_files %}
                <div class="form-check col-md-6 mb-2">
                    <input class="form-check-input file-cb" type="checkbox"
                        value="{{ f.id }}" id="f-cb-{{ f.id }}" {% if template and f in template.attachments %}checked{% endif %}>
                    <label class="form-check-label small text-truncate d-inline-block w-100" for="f-cb-{{ f.id }}" title="{{ f.filename }}">
                        {{ f.filename }} <span class="text-muted">({{ (f.file_size / 1024 / 1024)|round(2) }} МБ)</span>
                    </label>
                </div>
                {% endfor %}
                {% if not all_files %}
                <div class="col-12 text-muted small">
                    Нет загруженных файлов.
                </div>
                {% endif %}
            </div>
            
            <div class="mt-3 border-top pt-3">
                <label class="form-label small fw-bold text-dark mb-2">Или загрузите новые файлы прямо сейчас:</label>
                <input type="file" id="newFiles" class="form-control form-control-sm" multiple accept=".pdf,.docx,.xlsx">
                <div class="form-text small">Разрешены: PDF, DOCX, XLSX. До 50 МБ на файл.</div>
            </div>'''

new_files_html = '''<label class="form-label small fw-bold text-dark mb-3 mt-3">Прикрепленные файлы (инструкции, бланки, письма):</label>
            
            <div class="d-flex gap-3 mb-3">
                <button type="button" class="btn btn-sm btn-outline-copp" data-bs-toggle="modal" data-bs-target="#existingFilesModal">
                    <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" class="me-2"><path d="M4.5 3a2.5 2.5 0 0 1 5 0v9a1.5 1.5 0 0 1-3 0V5a.5.5 0 0 1 1 0v7a.5.5 0 0 0 1 0V3a1.5 1.5 0 1 0-3 0v9a2.5 2.5 0 0 0 5 0V5a.5.5 0 0 1 1 0v7a3.5 3.5 0 1 1-7 0V3z"/></svg>
                    Выбрать из уже загруженных
                </button>
                <button type="button" class="btn btn-sm btn-copp" onclick="document.getElementById('newFiles').click()">
                    <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" class="me-2"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/></svg>
                    Загрузить с ПК
                </button>
            </div>
            
            <input type="file" id="newFiles" class="d-none" multiple accept=".pdf,.docx,.xlsx" onchange="updateNewFilesCount()">
            <div id="newFilesStatus" class="form-text small mb-3 text-success d-none"></div>

            <div class="modal fade" id="existingFilesModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Выбрать из уже загруженных файлов</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row px-2">
                                {% for f in all_files %}
                                <div class="form-check col-md-6 mb-2">
                                    <input class="form-check-input file-cb" type="checkbox"
                                        value="{{ f.id }}" id="f-cb-{{ f.id }}" {% if template and f in template.attachments %}checked{% endif %}>
                                    <label class="form-check-label small text-truncate d-inline-block w-100" for="f-cb-{{ f.id }}" title="{{ f.filename }}">
                                        {{ f.filename }} <span class="text-muted">({{ (f.file_size / 1024 / 1024)|round(2) }} МБ)</span>
                                    </label>
                                </div>
                                {% endfor %}
                                {% if not all_files %}
                                <div class="col-12 text-muted small">
                                    Нет ранее загруженных файлов.
                                </div>
                                {% endif %}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Готово</button>
                        </div>
                    </div>
                </div>
            </div>'''

content = content.replace(old_files_html, new_files_html)

# 3. Add JS for updating new files count
js_snippet = '''    function updateNewFilesCount() {
        const input = document.getElementById('newFiles');
        const status = document.getElementById('newFilesStatus');
        if (input.files.length > 0) {
            status.textContent = `Выбрано файлов для загрузки: ${input.files.length}`;
            status.classList.remove('d-none');
        } else {
            status.classList.add('d-none');
        }
    }'''

content = content.replace('function addSheet()', js_snippet + '\n\n    function addSheet()')

with open("app/templates/constructor.html", "w") as f:
    f.write(content)
print("Constructor UI updated.")
