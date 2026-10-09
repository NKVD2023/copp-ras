import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from flask import render_template, send_file
from flask_login import login_required
from app.admin import admin_bp
from app.auth.decorators import roles_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.models.user import User, user_template_access
from app.models.logs import ActionLog
from app.models.report import ReportSubmission, ReportTemplate
from app.extensions import db

def get_stats_data_and_filters():
    """Сбор статистики по активности подотчетных пользователей (только role == 'user').
    Оптимизированная батчевая выборка (устранена проблема 400+ N+1 запросов к БД).
    """
    users = User.query.filter_by(role='user').options(joinedload(User.department)).all()
    if not users:
        return [], [], []

    user_ids = [u.id for u in users]

    # 1. Последний вход по всем пользователям за 1 запрос
    last_logins = dict(
        db.session.query(
            ActionLog.user_id,
            func.max(ActionLog.timestamp)
        ).filter(ActionLog.user_id.in_(user_ids), ActionLog.action == 'Вход в систему')
         .group_by(ActionLog.user_id).all()
    )

    # 2. Назначенные опубликованные шаблоны по всем пользователям за 1 запрос
    user_assigned_published = db.session.query(
        user_template_access.c.user_id,
        user_template_access.c.template_id
    ).join(ReportTemplate, user_template_access.c.template_id == ReportTemplate.id)\
     .filter(
         user_template_access.c.user_id.in_(user_ids),
         ReportTemplate.is_published == True,
         ReportTemplate.is_archived == False
     ).all()

    assigned_map = {}
    for u_id, t_id in user_assigned_published:
        assigned_map.setdefault(u_id, set()).add(t_id)

    # 3. Все сданные отчеты по пользователям за 1 запрос
    user_submissions = db.session.query(
        ReportSubmission.user_id,
        ReportSubmission.template_id,
        ReportSubmission.is_revision
    ).filter(ReportSubmission.user_id.in_(user_ids)).all()

    submitted_clean_map = {}  # u_id -> set of template_ids
    has_revisions_map = {}    # u_id -> bool
    submitted_count_map = {}  # u_id -> count of non-revision submissions

    for u_id, t_id, is_rev in user_submissions:
        if not is_rev:
            submitted_clean_map.setdefault(u_id, set()).add(t_id)
            submitted_count_map[u_id] = submitted_count_map.get(u_id, 0) + 1
        else:
            has_revisions_map[u_id] = True

    stats = []
    for user in users:
        last_login = last_logins.get(user.id)

        user_assigned_ids = assigned_map.get(user.id, set())
        assigned_templates_count = len(user_assigned_ids)

        user_clean_sub_ids = submitted_clean_map.get(user.id, set())
        submitted_reports_count = submitted_count_map.get(user.id, 0)
        has_revisions = has_revisions_map.get(user.id, False)

        # Пересечение: сданные шаблоны из числа назначенных
        dist_assigned_submitted = len(user_clean_sub_ids & user_assigned_ids)

        # Расчет процента сдачи
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
            'submitted': dist_assigned_submitted,
            'submitted_total': submitted_reports_count,
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
