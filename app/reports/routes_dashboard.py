"""
Модуль отчетов: Дашборд пользователя (Reports - Dashboard).
Отвечает за отображение главной панели для обычного пользователя (учреждения),
на которой показаны назначенные ему отчеты: сданные и ожидающие сдачи.
"""
from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission, User
from app.utils import is_mobile

# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ДАШБОРДЫ)
# ==========================================

@reports_bp.route('/')
@login_required
def dashboard():
    """
    Отображение главной панели.
    - Администраторов и наблюдателей автоматически перекидывает в админ-панель.
    - Обычному пользователю (учреждению) показывает карточки с отчетами,
      разделенные на две категории: "К заполнению" и "Завершенные".
    """
    if current_user.role in ['admin', 'manager']:
        return redirect(url_for('admin.dashboard'))
        
    # === ЛОГИКА ДЛЯ УЧРЕЖДЕНИЯ (USER) ===
    # Получаем все сданные отчеты напрямую из таблицы отправленных данных
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    filled_ids = [s.template_id for s in submissions]
    
    # Активные отчеты: назначенные, опубликованные
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    
    # Автоматическое закрытие отчетов с истекшим дедлайном
    needs_commit = False
    today = date.today()
    for t in assigned:
        if not t.is_completed and t.deadline and today > t.deadline:
            t.is_completed = True
            needs_commit = True
            
    if needs_commit:
        from app import db
        db.session.commit()
    
    # Архив пользователя (теперь "Завершенные отчеты"):
    # Сюда попадают отчеты, которые пользователь уже сдал ИЛИ которые глобально закрыты
    filled = [t for t in assigned if t.id in filled_ids or t.is_completed]
    # Сортируем завершенные новые сверху
    filled.sort(key=lambda x: x.id, reverse=True)
    
    # К заполнению: назначены, еще не сданные и не завершенные глобально
    unfilled = [t for t in assigned if t.id not in filled_ids and not t.is_completed]
    
    # Сортируем невыполненные по дедлайну (сначала те, что нужно сдать раньше)
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    active = unfilled  # все неотправленные — активные
    
    # Собираем все прикрепленные файлы из назначенных и сданных отчетов
    files_list = []
    seen_file_ids = set()
    for t in (unfilled + filled):
        for file in t.attachments:
            if file.id not in seen_file_ids:
                files_list.append({
                    'file': file,
                    'template_name': t.name
                })
                seen_file_ids.add(file.id)

    # Сортируем файлы по дате загрузки (сначала новые)
    files_list.sort(key=lambda x: x['file'].upload_date, reverse=True)
    
    # Модуль статистики для пользователя
    selected_short_name = request.args.get('short_name')
    stat_short_names = list(set([t.short_name for t in assigned if t.short_name and not t.is_template]))
    stat_short_names.sort()
    
    stat_schema = None
    if selected_short_name:
        from app.utils import build_table_headers
        matched_templates = ReportTemplate.query.filter_by(short_name=selected_short_name, is_template=False, is_published=True).order_by(ReportTemplate.id.desc()).all()
        # Оставляем только те, что назначены текущему пользователю
        matched_templates = [t for t in matched_templates if t in assigned]
        
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
                submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
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
                                    
    template_name = 'mobile/user_dashboard.html' if is_mobile(request) else 'user_dashboard.html'
    return render_template(template_name, 
                           unfilled_templates=active,
                           filled_templates=filled, 
                           attached_files=files_list,
                           stat_short_names=stat_short_names,
                           selected_short_name=selected_short_name,
                           stat_schema=stat_schema,
                           current_date=date.today())
