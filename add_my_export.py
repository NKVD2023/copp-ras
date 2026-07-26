import os

def update_export_my_excel():
    filepath = '/home/copp-admin/copp-ras/app/reports/routes_data.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('''

@reports_bp.route('/export_my_excel/<int:template_id>')
@login_required
def export_my_excel(template_id):
    """
    Генерация Excel-файла (.xlsx) с ответами текущего пользователя.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=current_user.id).first()
    
    if not submission:
        return "Отчет еще не заполнен", 400

    from app.services.excel_service import ExcelService
    from flask import send_file
    
    output, filename = ExcelService.export_report(template, [submission])
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f"Мой_отчет_{filename}"
    )
''')
    print("Added export_my_excel")

if __name__ == '__main__':
    update_export_my_excel()
