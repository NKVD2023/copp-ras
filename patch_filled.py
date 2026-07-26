import re

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's find the start of filledTab and replace it until the end of filledTab
start_idx = content.find('<div class="tab-pane fade" id="filledTab" role="tabpanel">')
# the end of filledTab is before <script>
end_idx = content.find('<script>', start_idx)

new_filled = """<div class="tab-pane fade" id="filledTab" role="tabpanel">
                <div class="row g-4" id="filledContainer">
                    {% for template in filled_templates %}
                    <div class="col-md-4 user-report-item" data-title="{{ template.name|lower }} {{ template.short_name|lower }}" data-deadline="{{ template.deadline.strftime('%Y-%m-%d') if template.deadline else '2099-12-31' }}" data-id="{{ template.id }}">
                        <div class="card h-100 p-2 border-success border-opacity-25 bg-light">
                            <div class="card-body d-flex flex-column justify-content-between">
                                <div>
                                    <div class="d-flex align-items-center gap-2 mb-2">
                                        <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 d-flex align-items-center gap-1">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/></svg>
                                            Успешно сдано
                                        </span>
                                        <span class="badge bg-white text-muted border">{{ template.period or '-' }}</span>
                                    </div>
                                    <h6 class="card-title fw-bold text-dark mb-1">{{ template.short_name or template.name }}</h6>
                                    <p class="text-muted small mb-3 line-clamp-2" title="{{ template.name }}">{{ template.name }}</p>
                                </div>
                                <div class="mt-auto pt-3 border-top border-success border-opacity-25 d-flex flex-column gap-2">
                                    <a href="{{ url_for('reports.fill_report', template_id=template.id) }}" class="btn btn-sm btn-outline-success w-100 d-flex align-items-center justify-content-center gap-2">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/><path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/></svg>
                                        Просмотреть ответы
                                    </a>
                                    <a href="{{ url_for('reports.export_my_excel', template_id=template.id) }}" class="btn btn-sm btn-success text-white w-100 d-flex align-items-center justify-content-center gap-2">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                                            <path d="M5.884 6.68a.5.5 0 1 0-.768.64L7.349 10l-2.233 2.68a.5.5 0 0 0 .768.64L8 10.781l2.116 2.54a.5.5 0 0 0 .768-.641L8.651 10l2.233-2.68a.5.5 0 0 0-.768-.64L8 9.219l-2.116-2.54z" />
                                            <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z" />
                                        </svg>
                                        Скачать в Excel
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% else %}
                    <div class="col-12">
                        <div class="text-center py-4 text-muted bg-white rounded border small">Архив сданных отчетов пуст.</div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- TAB: ФАЙЛЫ -->
            <div class="tab-pane fade" id="filesTab" role="tabpanel">
                <div class="card bg-white border-0 shadow-sm p-4">
                    {% if attached_files %}
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th>Имя файла</th>
                                    <th>Отчет</th>
                                    <th>Размер</th>
                                    <th>Загружен</th>
                                    <th>Действие</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in attached_files %}
                                <tr>
                                    <td>
                                        <div class="d-flex align-items-center gap-2">
                                            <i class="bi bi-file-earmark-text text-primary fs-5"></i>
                                            <span class="fw-medium text-dark">{{ item.file.filename }}</span>
                                        </div>
                                    </td>
                                    <td><span class="badge bg-light text-dark border">{{ item.template_name }}</span></td>
                                    <td class="text-muted small">{{ (item.file.file_size / 1024 / 1024)|round(2) }} МБ</td>
                                    <td class="text-muted small">{{ item.file.upload_date.strftime('%d.%m.%Y') }}</td>
                                    <td>
                                        <a href="{{ url_for('reports.download_file', file_id=item.file.id) }}" class="btn btn-sm btn-outline-primary" download>
                                            <i class="bi bi-download"></i> Скачать
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% else %}
                    <div class="text-center py-5 text-muted d-flex flex-column align-items-center">
                        <i class="bi bi-file-earmark-x" style="font-size: 3rem; color: #e2e8f0; margin-bottom: 1rem;"></i>
                        <span class="small">К вашим отчетам не прикреплено никаких файлов.</span>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        """

content = content[:start_idx] + new_filled + content[end_idx:]

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
