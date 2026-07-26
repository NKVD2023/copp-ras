import re

js_code = """
    <script>
        function exportExcel(btn, templateId) {
            const originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Запуск...';
            
            fetch(`/export_excel/${templateId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const taskId = data.task_id;
                        pollTaskStatus(taskId, btn, originalHtml);
                    } else {
                        alert("Ошибка запуска формирования файла");
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                    }
                })
                .catch(err => {
                    alert("Произошла ошибка при обращении к серверу");
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                });
        }
        
        function pollTaskStatus(taskId, btn, originalHtml) {
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Формируется...';
            fetch(`/task_status/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'SUCCESS') {
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                        window.location.href = `/task_download/${taskId}`;
                    } else if (data.status === 'FAILED') {
                        alert("Ошибка формирования файла: " + data.message);
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                    } else {
                        setTimeout(() => pollTaskStatus(taskId, btn, originalHtml), 1000);
                    }
                })
                .catch(err => {
                    setTimeout(() => pollTaskStatus(taskId, btn, originalHtml), 1000);
                });
        }
    </script>
"""

for filepath in ['/home/copp-admin/copp-ras/app/templates/admin_dashboard.html', '/home/copp-admin/copp-ras/app/templates/manager_dashboard.html']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if extra_js block exists
    if '{% block extra_js %}' in content:
        content = content.replace('{% block extra_js %}', '{% block extra_js %}' + js_code)
    else:
        # Just append it at the end
        content += "\n{% block extra_js %}" + js_code + "{% endblock %}"
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Updated JS successfully.")
