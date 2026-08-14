"""
Модуль администратора: Главная панель (Admin - Dashboard).
Отвечает за сбор всей статистики, отображение списков пользователей, отчетов,
бэкапов и логов. Также содержит глобальную функцию проверки прав для всех admin-маршрутов.
"""
import os
import datetime
from flask import render_template, request, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, ReportTemplate, ReportSubmission, ActionLog, UploadedFile
from app.auth.decorators import roles_required
from app import db
from config import basedir
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
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРД)
# ==========================================
@admin_bp.route('/')
def dashboard():
    """
    Основной маршрут панели администратора.
    Агрегирует данные из всех таблиц (пользователи, шаблоны, отчеты, логи, бэкапы)
    и передает их в единый шаблон `admin_dashboard.html`, который использует
    систему вкладок (tabs) для их отображения.
    """
    
    sort_param = request.args.get('sort')
    
    # 1. Данные пользователей (исключая текущего)
    users = User.query.filter(User.id != current_user.id).all()
    
    # 2. Список шаблонов (новые сверху)
    all_templates = ReportTemplate.query.order_by(ReportTemplate.id.desc()).all()
    
    # 3. Собираем словарь должников и распределяем шаблоны
    debtors_map, pure_templates, published_templates, draft_templates, archived_templates, completed_templates = TemplateService.get_dashboard_stats(all_templates)

    pure_templates = TemplateService.sort_templates(pure_templates, sort_param or 'deadline_asc')
    published_templates = TemplateService.sort_templates(published_templates, sort_param or 'deadline_asc')
    draft_templates = TemplateService.sort_templates(draft_templates, sort_param or 'deadline_asc')
    archived_templates = TemplateService.sort_templates(archived_templates, sort_param or 'deadline_asc')
    completed_templates = TemplateService.sort_templates(completed_templates, sort_param or 'id_desc')

    # Данные для вкладки "База Данных" и "Сданные отчёты" (если нужны)
    all_users = User.query.all()
    all_submissions = ReportSubmission.query.order_by(ReportSubmission.id.desc()).all()
    active_submissions = [sub for sub in all_submissions if getattr(sub, 'is_archived', False) == False]

    # 4. Сканируем папку backups для отображения списка резервных копий
    backups_dir = os.path.join(basedir, 'backups')
    backups_list = []
    if os.path.exists(backups_dir):
        for f in os.listdir(backups_dir):
            if f.endswith('.db'):
                path = os.path.join(backups_dir, f)
                stat = os.stat(path)
                backups_list.append({
                    'name': f,
                    'size': stat.st_size,           # Размер файла
                    'mtime': stat.st_mtime          # Время изменения
                })
        # Сортируем: свежие бэкапы сверху
        backups_list.sort(key=lambda x: x['mtime'], reverse=True)
        
    # 5. Загружаем последние 500 записей журнала действий
    logs_list = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(500).all()

    # 6. Получение всех уникальных существующих групп
    groups_query = db.session.query(User.group).filter(User.group.isnot(None), User.group != '').distinct().all()
    all_groups = sorted([g[0] for g in groups_query if g[0]])
    if not all_groups:
        all_groups = ['СПО', 'ВУЗ', 'Школы', 'Работодатели']

    # 6. Файлы
    all_files = UploadedFile.query.order_by(UploadedFile.upload_date.desc()).all()

    from app.models import Dictionary
    dictionaries = Dictionary.query.order_by(Dictionary.name).all()

    # 9. Модуль статистики (Динамика)
    selected_user_id = request.args.get('user_id')
    selected_short_name = request.args.get('short_name')
    
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

    # Передаем весь этот массив данных в шаблон
    return render_template('admin_dashboard.html', 
                           users=users, 
                           templates=all_templates, 
                           pure_templates=pure_templates,
                           published_templates=published_templates,
                           draft_templates=draft_templates,
                           archived_templates=archived_templates,
                           completed_templates=completed_templates,
                           debtors_map=debtors_map,
                           all_users=all_users,
                           all_submissions=all_submissions,
                           active_submissions=active_submissions,
                           backups_list=backups_list,
                           logs_list=logs_list,
                           all_groups=all_groups,
                           all_files=all_files,
                           dictionaries=dictionaries,
                           stat_short_names=stat_short_names,
                           selected_user_id=int(selected_user_id) if selected_user_id and selected_user_id.isdigit() else None,
                           selected_short_name=selected_short_name,
                           stat_schema=stat_schema,
                           current_sort=sort_param,
                           current_date=datetime.date.today())


@admin_bp.route('/clear_logs', methods=['POST'])
@login_required
@roles_required('admin')
def clear_logs():
    """
    Маршрут для полной очистки таблицы `action_logs`.
    Доступен исключительно администратору (viewer не может удалять логи).
    """
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
        
    ActionLog.query.delete()
    db.session.commit()
    
    # Сразу после очистки добавим лог о том, кто именно её произвел
    from app.utils import log_action
    log_action('Очистка логов', f'Администратор {current_user.username} полностью очистил журнал действий')
    
    return redirect(url_for('admin.dashboard') + '#logsTab')

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