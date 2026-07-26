import os

def update_export_excel():
    filepath = '/home/copp-admin/copp-ras/app/reports/routes_data.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('@reports_bp.route(\'/export_excel/<int:template_id>\')'):
            start_idx = i
            break
            
    if start_idx != -1:
        new_content = "".join(lines[:start_idx])
        new_content += """@reports_bp.route('/export_excel/<int:template_id>')
@login_required
def export_excel(template_id):
    if current_user.role not in ['admin', 'manager']:
        return "Доступ ограничен", 403
        
    from app.services.task_service import TaskService
    task_id = TaskService.start_excel_generation(template_id, current_user.id)
    return jsonify({'status': 'success', 'task_id': task_id})
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated export_excel")
    else:
        print("Could not find export_excel")

if __name__ == '__main__':
    update_export_excel()
