"""
Модуль администратора: Главная панель (Admin - Dashboard).
Отвечает за сбор всей статистики, отображение списков пользователей, отчетов,
бэкапов и логов. Также содержит глобальную функцию проверки прав для всех admin-маршрутов.
"""
import os
import datetime
from flask import render_template, request, redirect, url_for, send_file, jsonify
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission, ActionLog, UploadedFile, Announcement
from app.auth.decorators import roles_required
from app.extensions import db
from config import basedir
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy import func
from app.models import user_template_access
from app.models.report import report_attachments
from app.services.template_service import TemplateService
from app.services.excel_service import ExcelService

# ==========================================
# ПРОВЕРКА ПРАВ ДОСТУПА ДЛЯ ВСЕХ МАРШРУТОВ
# ==========================================
@admin_bp.before_request
@login_required
def require_admin():
    """
    Middleware: Перехватывает каждый запрос к админ-панели (с префиксом /admin).
    - Разрешает доступ только пользователям с ролями 'admin' и 'manager'.
    - Обычных пользователей перенаправляет на их личный дашборд.
    """
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('reports.dashboard'))

# ==========================================
# МОДУЛЬНЫЕ СБОРЩИКИ КОНТЕКСТА ВКЛАДОК (LAZY TABS)
# ==========================================

def _get_manager_dept(user):
    if user.role == 'manager':
        from app.utils import get_manager_department
        return get_manager_department(user)
    return None

def _get_users_tab_context(user):
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            users = dept.members.options(joinedload(User.department)).filter(User.id != user.id).all()
            templates = dept.templates.order_by(ReportTemplate.id.desc()).all()
            dept_users = dept.members.all()
            all_groups = sorted(list(set([u.group for u in dept_users if u.group])))
        else:
            users = []
            templates = []
            all_groups = []
        departments = [dept] if dept else []
    else:
        from app.models import Department
        users = User.query.options(joinedload(User.department)).filter(User.id != user.id).all()
        templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
        groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
        all_groups = sorted([g[0] for g in groups_query if g[0]])
        if not all_groups:
            all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']
        departments = Department.query.order_by(Department.name).all()

    user_assigned_pairs = set(
        db.session.query(user_template_access.c.user_id, user_template_access.c.template_id).all()
    )
    user_assigned_dict = {}
    for uid, tid in user_assigned_pairs:
        user_assigned_dict.setdefault(uid, []).append(tid)

    return {
        'users': users,
        'templates': templates,
        'all_groups': all_groups,
        'departments': departments,
        'user_assigned_pairs': user_assigned_pairs,
        'user_assigned_dict': user_assigned_dict,
    }

def _get_reports_tab_context(user, sort_param=None):
    from app.models.department import department_templates, Department
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            users = dept.members.options(joinedload(User.department)).filter(User.id != user.id).all()
            all_templates = dept.templates.options(subqueryload(ReportTemplate.attachments)).order_by(ReportTemplate.id.desc()).all()
        else:
            users = []
            all_templates = []
        departments = [dept] if dept else []
    else:
        users = User.query.options(joinedload(User.department)).filter(User.id != user.id).all()
        all_templates = ReportTemplate.query.options(subqueryload(ReportTemplate.attachments)).order_by(ReportTemplate.id.desc()).all()
        departments = Department.query.order_by(Department.name).all()

    debtors_map, revisions_map, pure_templates, published_templates, revision_templates, draft_templates, archived_templates, completed_templates, assigned_counts = TemplateService.get_dashboard_stats(all_templates)

    pure_templates = TemplateService.sort_templates(pure_templates, sort_param or 'deadline_asc')
    published_templates = TemplateService.sort_templates(published_templates, sort_param or 'deadline_asc')
    revision_templates = TemplateService.sort_templates(revision_templates, sort_param or 'deadline_asc')
    draft_templates = TemplateService.sort_templates(draft_templates, sort_param or 'deadline_asc')
    archived_templates = TemplateService.sort_templates(archived_templates, sort_param or 'deadline_asc')
    completed_templates = TemplateService.sort_templates(completed_templates, sort_param or 'id_desc')

    user_assigned_pairs = set(
        db.session.query(user_template_access.c.user_id, user_template_access.c.template_id).all()
    )
    report_attachment_pairs = set(
        db.session.query(report_attachments.c.template_id, report_attachments.c.file_id).all()
    )
    report_attachment_counts = dict(
        db.session.query(report_attachments.c.template_id, func.count()).group_by(report_attachments.c.template_id).all()
    )
    template_submissions_counts = dict(
        db.session.query(ReportSubmission.template_id, func.count()).group_by(ReportSubmission.template_id).all()
    )

    template_departments_raw = db.session.query(
        department_templates.c.template_id,
        Department.name
    ).join(Department, department_templates.c.department_id == Department.id).all()
    template_departments_map = {}
    for tid, dname in template_departments_raw:
        template_departments_map.setdefault(tid, []).append(dname)

    dept_template_pairs = set(
        db.session.query(department_templates.c.department_id, department_templates.c.template_id).all()
    )

    all_groups = sorted(list(set([u.group for u in users if u.group])))
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']

    template_assigned_dict = {}
    for uid, tid in user_assigned_pairs:
        template_assigned_dict.setdefault(tid, []).append(uid)

    return {
        'templates': all_templates,
        'all_groups': all_groups,
        'pure_templates': pure_templates,
        'published_templates': published_templates,
        'revision_templates': revision_templates,
        'draft_templates': draft_templates,
        'archived_templates': archived_templates,
        'completed_templates': completed_templates,
        'debtors_map': debtors_map,
        'revisions_map': revisions_map,
        'assigned_counts': assigned_counts,
        'user_assigned_pairs': user_assigned_pairs,
        'template_assigned_dict': template_assigned_dict,
        'report_attachment_pairs': report_attachment_pairs,
        'report_attachment_counts': report_attachment_counts,
        'template_submissions_counts': template_submissions_counts,
        'template_departments_map': template_departments_map,
        'dept_template_pairs': dept_template_pairs,
        'users': users,
        'departments': departments,
        'current_sort': sort_param,
        'current_date': datetime.date.today(),
    }

def _get_lists_tab_context(user):
    from app.models import Dictionary, Department
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            dictionaries = Dictionary.query.filter_by(department_id=dept.id).order_by(Dictionary.name).all()
        else:
            dictionaries = []
        departments = [dept] if dept else []
    else:
        dictionaries = Dictionary.query.order_by(Dictionary.name).all()
        departments = Department.query.order_by(Department.name).all()

    return {
        'dictionaries': dictionaries,
        'departments': departments,
    }

def _get_files_tab_context(user):
    from app.models import Department
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            all_files = UploadedFile.query.options(joinedload(UploadedFile.uploader)).filter_by(department_id=dept.id).order_by(UploadedFile.upload_date.desc()).all()
        else:
            all_files = []
        departments = [dept] if dept else []
    else:
        all_files = UploadedFile.query.options(joinedload(UploadedFile.uploader)).order_by(UploadedFile.upload_date.desc()).all()
        departments = Department.query.order_by(Department.name).all()

    file_report_counts = dict(
        db.session.query(report_attachments.c.file_id, func.count()).group_by(report_attachments.c.file_id).all()
    )

    return {
        'all_files': all_files,
        'file_report_counts': file_report_counts,
        'departments': departments,
    }

def _get_announcements_tab_context(user):
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            announcements = Announcement.query.options(joinedload(Announcement.author)).filter(
                (Announcement.created_by_id == user.id) |
                (Announcement.target_type == 'all')
            ).order_by(Announcement.created_at.desc()).all()
            dept_users = dept.members.all()
            all_groups = sorted(list(set([u.group for u in dept_users if u.group])))
        else:
            announcements = []
            all_groups = []
    else:
        announcements = Announcement.query.options(joinedload(Announcement.author)).order_by(Announcement.created_at.desc()).all()
        groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
        all_groups = sorted([g[0] for g in groups_query if g[0]])
        if not all_groups:
            all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']

    return {
        'announcements': announcements,
        'all_groups': all_groups,
    }

def _get_departments_tab_context(user):
    from app.models import Department, Dictionary
    from app.models.department import department_templates
    departments = Department.query.order_by(Department.name).all()
    dept_member_counts = dict(
        db.session.query(User.department_id, func.count()).filter(User.department_id.isnot(None)).group_by(User.department_id).all()
    )
    templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    pure_templates = [t for t in templates if getattr(t, 'is_template', False)]
    published_templates = [t for t in templates if getattr(t, 'is_published', False) and not getattr(t, 'is_completed', False) and not getattr(t, 'is_archived', False)]
    completed_templates = [t for t in templates if getattr(t, 'is_completed', False) and not getattr(t, 'is_archived', False)]
    archived_templates = [t for t in templates if getattr(t, 'is_archived', False)]
    draft_templates = [t for t in templates if not getattr(t, 'is_template', False) and not getattr(t, 'is_published', False) and not getattr(t, 'is_completed', False) and not getattr(t, 'is_archived', False)]

    dept_template_pairs = set(
        db.session.query(department_templates.c.department_id, department_templates.c.template_id).all()
    )
    users = User.query.filter(User.id != user.id).all()
    all_files = UploadedFile.query.all()
    dictionaries = Dictionary.query.all()

    return {
        'departments': departments,
        'dept_member_counts': dept_member_counts,
        'templates': templates,
        'pure_templates': pure_templates,
        'published_templates': published_templates,
        'completed_templates': completed_templates,
        'archived_templates': archived_templates,
        'draft_templates': draft_templates,
        'dept_template_pairs': dept_template_pairs,
        'users': users,
        'all_files': all_files,
        'dictionaries': dictionaries,
    }

def _get_statistics_tab_context(user, selected_user_id=None, selected_short_name=None):
    dept = _get_manager_dept(user)
    if user.role == 'manager':
        if dept:
            users = dept.members.options(joinedload(User.department)).filter(User.id != user.id).all()
            all_templates = dept.templates.order_by(ReportTemplate.id.desc()).all()
        else:
            users = []
            all_templates = []
    else:
        users = User.query.options(joinedload(User.department)).filter(User.id != user.id).all()
        all_templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()

    stat_short_names = list(set([t.short_name for t in all_templates if t.short_name and not t.is_template]))
    stat_short_names.sort()

    stat_schema = None
    if selected_user_id and selected_short_name:
        from app.utils import build_table_headers
        matched_templates = ReportTemplate.query.filter_by(short_name=selected_short_name, is_template=False).order_by(ReportTemplate.id.desc()).all()
        if matched_templates:
            latest_template = matched_templates[0]
            import copy
            stat_schema = copy.deepcopy(latest_template.schema)
            for sheet in stat_schema:
                fields = sheet.get('fields', [])
                header_rows, leaf_fields = build_table_headers(fields)
                sheet['header_rows'] = header_rows
                sheet['leaf_fields'] = leaf_fields
                sheet['periods_data'] = []
                
            for template in matched_templates:
                submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=selected_user_id).first()
                period_name = template.period or f"Период {template.id}"
                
                for sheet in stat_schema:
                    sheet_data = {
                        'period': period_name,
                        'template_id': template.id,
                        'has_submission': submission is not None,
                        'values': submission.data if submission else {}
                    }
                    sheet['periods_data'].append(sheet_data)
                    
            for sheet in stat_schema:
                periods_data = sheet['periods_data']
                for i in range(len(periods_data) - 1):
                    curr = periods_data[i]
                    prev = periods_data[i+1]
                    if curr['has_submission'] and prev['has_submission']:
                        curr['deltas'] = {}
                        for field in sheet['leaf_fields']:
                            f_id = str(field.get('name') or field.get('id', ''))
                            if not f_id: continue
                            if field.get('type') == 'number':
                                cv_raw = curr['values'].get(f_id)
                                pv_raw = prev['values'].get(f_id)
                                try:
                                    cv = float(cv_raw) if cv_raw not in [None, ""] else 0.0
                                    pv = float(pv_raw) if pv_raw not in [None, ""] else 0.0
                                    curr['deltas'][f_id] = cv - pv
                                except (ValueError, TypeError):
                                    pass

    return {
        'users': users,
        'stat_short_names': stat_short_names,
        'selected_user_id': int(selected_user_id) if selected_user_id and str(selected_user_id).isdigit() else None,
        'selected_short_name': selected_short_name,
        'stat_schema': stat_schema,
    }

def _get_database_tab_context(user):
    from app.models import Department, ReportDraft, BackgroundTask, MaintenanceSetting, Dictionary
    import sqlite3

    all_users = User.query.options(joinedload(User.department)).all()
    all_templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    total_submissions_count = ReportSubmission.query.count()
    all_submissions = ReportSubmission.query.options(
        joinedload(ReportSubmission.template),
        joinedload(ReportSubmission.user)
    ).order_by(ReportSubmission.id.desc()).limit(100).all()
    active_submissions = [sub for sub in all_submissions if getattr(sub, 'is_archived', False) == False]
    all_departments = Department.query.order_by(Department.name).all()
    total_drafts_count = ReportDraft.query.count()
    all_drafts = ReportDraft.query.options(
        joinedload(ReportDraft.template),
        joinedload(ReportDraft.user)
    ).order_by(ReportDraft.updated_at.desc()).limit(100).all()
    all_tasks = BackgroundTask.query.order_by(BackgroundTask.created_at.desc()).limit(100).all()
    all_maintenance = MaintenanceSetting.query.all()
    dictionaries = Dictionary.query.order_by(Dictionary.name).all()
    all_files = UploadedFile.query.options(joinedload(UploadedFile.uploader)).order_by(UploadedFile.upload_date.desc()).all()

    backups_dir = os.path.join(basedir, 'backups')
    backups_list = []
    if os.path.exists(backups_dir):
        for f in os.listdir(backups_dir):
            if f.endswith('.db'):
                path = os.path.join(backups_dir, f)
                stat = os.stat(path)
                backups_list.append({
                    'name': f,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                })
        backups_list.sort(key=lambda x: x['mtime'], reverse=True)

    db_path = os.path.join(basedir, 'reports.db')
    db_size_mb = 0.0
    if os.path.exists(db_path):
        db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        
    total_records = (
        len(all_users) + len(all_templates) + total_submissions_count + 
        len(all_departments) + total_drafts_count + len(dictionaries) + 
        len(all_files) + len(all_tasks)
    )
    
    db_stats = {
        'size_mb': db_size_mb,
        'total_records': total_records,
        'sqlite_version': sqlite3.sqlite_version,
        'backups_count': len(backups_list),
        'latest_backup': backups_list[0] if backups_list else None,
        'tables_count': 9
    }

    return {
        'all_users': all_users,
        'templates': all_templates,
        'all_submissions': all_submissions,
        'total_submissions_count': total_submissions_count,
        'active_submissions': active_submissions,
        'all_drafts': all_drafts,
        'total_drafts_count': total_drafts_count,
        'all_tasks': all_tasks,
        'all_maintenance': all_maintenance,
        'backups_list': backups_list,
        'db_stats': db_stats,
        'departments': all_departments,
        'dictionaries': dictionaries,
        'all_files': all_files,
    }

def _get_logs_tab_context(user):
    return {
        'logs_list': [],
    }

ADMIN_ONLY_TABS = {'users', 'departments', 'database', 'logs'}

TAB_CONTEXT_BUILDERS = {
    'users': lambda u, req: _get_users_tab_context(u),
    'reports': lambda u, req: _get_reports_tab_context(u, sort_param=req.args.get('sort') if req else None),
    'lists': lambda u, req: _get_lists_tab_context(u),
    'files': lambda u, req: _get_files_tab_context(u),
    'announcements': lambda u, req: _get_announcements_tab_context(u),
    'departments': lambda u, req: _get_departments_tab_context(u),
    'statistics': lambda u, req: _get_statistics_tab_context(
        u,
        selected_user_id=req.args.get('user_id') if req else None,
        selected_short_name=req.args.get('short_name') if req else None
    ),
    'database': lambda u, req: _get_database_tab_context(u),
    'logs': lambda u, req: _get_logs_tab_context(u),
}

TAB_TEMPLATES = {
    'users': 'admin_tabs/users_tabs.html',
    'reports': 'admin_tabs/reports_wrapper.html',
    'lists': 'admin_tabs/lists_tabs.html',
    'files': 'admin_tabs/files_wrapper.html',
    'announcements': 'admin_tabs/announcements_tabs.html',
    'departments': 'admin_tabs/departments_tabs.html',
    'statistics': 'admin_tabs/statistics/statistics_main.html',
    'database': 'admin_tabs/db_tabs.html',
    'logs': 'admin_tabs/logs_tabs.html',
}

# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРД С ЛЕНИВОЙ ЗАГРУЗКОЙ)
# ==========================================
@admin_bp.route('/')
def dashboard():
    """
    Основной маршрут панели администратора.
    Использует архитектуру Lazy Tabs: генерирует данные ТОЛЬКО для активной вкладки,
    а остальные вкладки подгружаются асинхронно по требованию через /admin/tab/<tab_name>.
    """
    req_tab = request.args.get('tab', '')
    selected_user_id = request.args.get('user_id')
    selected_short_name = request.args.get('short_name')
    sort_param = request.args.get('sort')
    
    if selected_user_id or selected_short_name:
        active_tab_key = 'statistics'
    elif sort_param:
        active_tab_key = 'reports'
    elif req_tab:
        clean = req_tab[:-3] if req_tab.endswith('Tab') else req_tab
        active_tab_key = clean.lower()
    elif current_user.role == 'admin':
        active_tab_key = 'users'
    else:
        active_tab_key = 'reports'

    # Проверка прав доступа к административным вкладкам
    if current_user.role != 'admin' and active_tab_key in ADMIN_ONLY_TABS:
        active_tab_key = 'reports'

    builder = TAB_CONTEXT_BUILDERS.get(
        active_tab_key,
        TAB_CONTEXT_BUILDERS['users'] if current_user.role == 'admin' else TAB_CONTEXT_BUILDERS['reports']
    )
    tab_context = builder(current_user, request)

    context = {
        'active_tab': active_tab_key + 'Tab',
        'active_tab_key': active_tab_key,
        'selected_user_id': int(selected_user_id) if selected_user_id and selected_user_id.isdigit() else None,
        'selected_short_name': selected_short_name,
        'current_date': datetime.date.today(),
        **tab_context
    }
    return render_template('admin_dashboard.html', **context)


@admin_bp.route('/tab/<tab_name>')
def get_tab_fragment(tab_name):
    """
    Эндпоинт ленивой подгрузки фрагментов вкладок (Lazy Tabs).
    Возвращает сгенерированный HTML только запрошенного раздела.
    """
    clean_name = tab_name[:-3] if tab_name.endswith('Tab') else tab_name
    clean_name = clean_name.lower()

    if clean_name not in TAB_TEMPLATES:
        return "<div class='alert alert-danger m-3'>Вкладка не найдена</div>", 404

    if current_user.role != 'admin' and clean_name in ADMIN_ONLY_TABS:
        return "<div class='alert alert-danger m-3'>Доступ запрещен</div>", 403

    builder = TAB_CONTEXT_BUILDERS.get(clean_name)
    tab_context = builder(current_user, request)
    template_file = TAB_TEMPLATES[clean_name]

    return render_template(template_file, **tab_context)


@admin_bp.route('/clear_logs', methods=['POST'])
@login_required
@roles_required('admin')
def clear_logs():
    """
    Маршрут для очистки таблицы `action_logs`.
    Поддерживает полную очистку или очистку старых записей (старше 6 мес., 1 года).
    Доступен исключительно администратору.
    """
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Доступ запрещен'}), 403
        
    older_than = request.form.get('older_than', 'all')
    from datetime import datetime, timedelta
    
    if older_than == '180_days':
        threshold = datetime.utcnow() - timedelta(days=180)
        deleted = ActionLog.query.filter(ActionLog.timestamp < threshold).delete()
        msg = f'очистил записи старше 6 месяцев (удалено {deleted} записей)'
    elif older_than == '365_days':
        threshold = datetime.utcnow() - timedelta(days=365)
        deleted = ActionLog.query.filter(ActionLog.timestamp < threshold).delete()
        msg = f'очистил записи старше 1 года (удалено {deleted} записей)'
    else:
        deleted = ActionLog.query.delete()
        msg = f'полностью очистил журнал действий (удалено {deleted} записей)'
        
    db.session.commit()
    
    # Сразу после очистки добавим лог о том, кто именно её произвел
    from app.utils import log_action
    log_action('Очистка логов', f'Администратор {current_user.username} {msg}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success', 'message': f'Журнал обновлен: {msg}'})
        
    return redirect(url_for('admin.dashboard', tab='logsTab'))

@admin_bp.route('/export_statistics', methods=['GET'])
@login_required
def export_admin_statistics():
    selected_user_id = request.args.get('user_id', type=int)
    selected_short_name = request.args.get('short_name')

    if not selected_user_id or not selected_short_name:
        return redirect(url_for('admin.dashboard', tab='statisticsTab'))

    user = User.query.get_or_404(selected_user_id)
    user_title = user.description if user.description else user.username

    # Находим опубликованные шаблоны данного типа, назначенные этому пользователю
    templates = ReportTemplate.query.filter_by(
        short_name=selected_short_name,
        is_published=True,
        is_template=False
    ).order_by(ReportTemplate.id.asc()).all()

    assigned_templates = [
        t for t in templates
        if any(a.id == user.id for a in t.assigned_users)
    ]

    if not assigned_templates:
        return redirect(url_for('admin.dashboard', tab='statisticsTab'))

    from app.services.stat_service import StatService
    stat_schema = StatService.build_stat_schema_for_export(assigned_templates, user.id)

    if not stat_schema:
        return redirect(url_for('admin.dashboard', tab='statisticsTab'))

    output, filename = ExcelService.export_statistics(stat_schema, selected_short_name, user_title)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
@admin_bp.route('/repair_db')
@login_required
@roles_required('admin')
def repair_db():
    from app.models import ReportTemplate
    from sqlalchemy.orm.attributes import flag_modified
    from sqlalchemy import text
    import json
    
    # 1. Починка структуры БД (добавление колонки department_id)
    try:
        db.session.execute(text("ALTER TABLE users ADD COLUMN department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass

    try:
        db.session.execute(text("ALTER TABLE uploaded_files ADD COLUMN department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass

    try:
        db.session.execute(text("ALTER TABLE dictionaries ADD COLUMN department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL;"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass

    # 2. Починка JSON схемы отчетов
    templates = ReportTemplate.query.all()
    repaired_count = 0
    
    for t in templates:
        if not t.schema:
            continue
            
        modified = False
        schema_data = t.schema
        if isinstance(schema_data, str):
            try:
                schema_data = json.loads(schema_data)
            except:
                continue
                
        for sheet in schema_data:
            for field in sheet.get('fields', []):
                if not field.get('name'):
                    field_id = field.get('id')
                    if field_id:
                        field['name'] = field_id
                        modified = True
                        if field.get('is_active') is False:
                            field['is_active'] = True
                            
        if modified:
            t.schema = schema_data
            flag_modified(t, 'schema')
            repaired_count += 1
            
    db.session.commit()
    return f"Готово! Восстановлено шаблонов: {repaired_count}. Теперь можете вернуться в отчеты."
