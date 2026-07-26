from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from datetime import date
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import re
from app import db
from app.models import ReportTemplate, ReportSubmission, User
from app.services.excel_service import ExcelService
from app.auth.decorators import roles_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def dashboard():
    if current_user.role in ['admin', 'manager']:
        return redirect(url_for('admin.dashboard'))
        
    sort_param = request.args.get('sort', 'deadline_asc')
    
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    
    unfilled = [t for t in assigned if t.id not in filled_ids]
    filled = [t for t in assigned if t.id in filled_ids]
    
    def sort_templates(templates, sort_by):
        if sort_by == 'deadline_asc':
            return sorted(templates, key=lambda x: x.deadline or date.max)
        elif sort_by == 'deadline_desc':
            return sorted(templates, key=lambda x: x.deadline or date.min, reverse=True)
        elif sort_by == 'name_asc':
            return sorted(templates, key=lambda x: x.name.lower())
        elif sort_by == 'name_desc':
            return sorted(templates, key=lambda x: x.name.lower(), reverse=True)
        elif sort_by == 'id_desc':
            return sorted(templates, key=lambda x: x.id, reverse=True)
        return sorted(templates, key=lambda x: x.deadline or date.max)

    unfilled = sort_templates(unfilled, sort_param)
    filled = sort_templates(filled, sort_param)
    return render_template('user_dashboard.html', unfilled_templates=unfilled, filled_templates=filled, current_sort=sort_param, current_date=date.today())

@reports_bp.route('/fill/<int:template_id>', methods=['GET', 'POST'])
@login_required
def fill_report(template_id):
    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role != 'user' or template not in current_user.assigned_templates or not template.is_published:
        return "Доступ ограничен или форма не опубликована", 403
        
    is_locked = template.deadline and date.today() > template.deadline
    submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
    
    if request.method == 'POST':
        if is_locked:
            return jsonify({'status': 'error', 'message': 'Дедлайн прошел. Редактирование запрещено.'}), 403
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=current_user.id)
            db.session.add(submission)
        submission.data = request.get_json()
        db.session.commit()
        return jsonify({'status': 'success'})
        
    return render_template('fill_report.html', template=template, submission=submission, is_locked=is_locked)

@reports_bp.route('/view_data/<int:template_id>')
@login_required
@roles_required('admin', 'manager')
def view_data(template_id):
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()
    return render_template('report_data_view.html', template=template, submissions=submissions)


@reports_bp.route('/export_excel/<int:template_id>')
@login_required
@roles_required('admin', 'manager')
def export_excel(template_id):
    template = ReportTemplate.query.get_or_404(template_id)
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()

    output, filename = ExcelService.export_report(template, submissions)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )