import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from flask import render_template, send_file
from flask_login import login_required
from app.admin import admin_bp
from app.auth.decorators import roles_required
from app.models.user import User
from app.models.logs import ActionLog
from app.models.report import ReportSubmission
from app.extensions import db

def get_stats_data_and_filters():
    """Сбор статистики по активности подотчетных пользователей (только role == 'user')."""
    users = User.query.filter_by(role='user').all()
    stats = []

    for user in users:
        # Last login
        last_login_log = ActionLog.query.filter_by(user_id=user.id, action='Вход в систему').order_by(ActionLog.timestamp.desc()).first()
        last_login = last_login_log.timestamp if last_login_log else None

        # Assigned published templates count
        assigned_templates = [t for t in user.assigned_templates if t.is_published and not getattr(t, 'is_archived', False)]
        assigned_templates_count = len(assigned_templates)
        assigned_template_ids = {t.id for t in assigned_templates}

        # Submitted reports count (только принятые, не на доработке)
        submitted_reports_count = ReportSubmission.query.filter_by(user_id=user.id, is_revision=False).count()
        has_revisions = ReportSubmission.query.filter_by(user_id=user.id, is_revision=True).count() > 0

        # Distinct submitted assigned templates
        dist_assigned_submitted = db.session.query(ReportSubmission.template_id)\
            .filter(ReportSubmission.user_id == user.id, ReportSubmission.is_revision == False, ReportSubmission.template_id.in_(assigned_template_ids))\
            .distinct().count() if assigned_template_ids else 0

        # Completion rate
        completion_rate = 0.0
        if assigned_templates_count > 0:
            if dist_assigned_submitted > 0:
                completion_rate = min(100.0, round((dist_assigned_submitted / assigned_templates_count) * 100, 1))
            elif submitted_reports_count > 0:
                completion_rate = min(100.0, round((submitted_reports_count / assigned_templates_count) * 100, 1))

        # Официальные строгие статусы
        if not last_login:
            status = 'Не входил'
        elif assigned_templates_count == 0:
            status = 'Сдано' if submitted_reports_count > 0 else 'Без назначений'
        elif completion_rate >= 100:
            status = 'Сдано полностью'
        elif has_revisions:
            status = 'На доработке'
        elif completion_rate > 0:
            status = 'В процессе'
        else:
            status = 'Отчеты не сданы'
            
        stats.append({
            'username': user.username,
            'description': user.description or '',
            'group': user.group or '',
            'department': user.department.name if user.department else '',
            'last_login': last_login,
            'assigned': assigned_templates_count,
            'submitted': submitted_reports_count,
            'completion_rate': completion_rate,
            'status': status
        })
    
    # Sort stats by completion_rate desc, then by username
    stats.sort(key=lambda x: (x['completion_rate'], x['username']), reverse=True)
    
    groups = sorted(list({s['group'] for s in stats if s['group']}))
    departments = sorted(list({s['department'] for s in stats if s['department']}))

    return stats, groups, departments

@admin_bp.route('/db/activity/generate')
@login_required
@roles_required('admin')
def db_activity_generate():
    stats, groups, departments = get_stats_data_and_filters()
    return render_template(
        'admin_tabs/db/activity_stats_result.html',
        stats=stats,
        all_groups=groups,
        all_departments=departments
    )

@admin_bp.route('/db/activity/export')
@login_required
@roles_required('admin')
def db_activity_export():
    stats, _, _ = get_stats_data_and_filters()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Статистика активности"
    
    headers = [
        "Логин",
        "ФИО / Наименование",
        "Группа",
        "Отдел",
        "Последний вход",
        "Назначено отчетов",
        "Сдано отчетов",
        "Процент выполнения (%)",
        "Статус"
    ]
    ws.append(headers)
    
    # Header styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="005B8C", end_color="005B8C", fill_type="solid")
    
    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    for s in stats:
        last_login_str = s['last_login'].strftime('%d.%m.%Y %H:%M') if s['last_login'] else 'Никогда'
        ws.append([
            s['username'],
            s['description'],
            s['group'],
            s['department'],
            last_login_str,
            s['assigned'],
            s['submitted'],
            f"{s['completion_rate']}%",
            s['status']
        ])
    
    # Column widths
    column_widths = {
        'A': 22,
        'B': 35,
        'C': 20,
        'D': 25,
        'E': 22,
        'F': 20,
        'G': 18,
        'H': 24,
        'I': 18
    }
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"activity_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
