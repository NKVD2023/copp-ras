"""
Модуль отчетов: Дашборд пользователя (Reports - Dashboard).
Отвечает за отображение главной панели для обычного пользователя (учреждения),
на которой показаны назначенные ему отчеты: сданные и ожидающие сдачи.
"""
from flask import render_template, redirect, url_for, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import date
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission, User, Announcement
from app.utils import is_mobile
from app.services.excel_service import ExcelService

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
    # Отчет считается сданным только если он не находится на доработке
    filled_ids = [s.template_id for s in submissions if not s.is_revision]
    revision_submissions = {s.template_id: s for s in submissions if s.is_revision}
    
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
        from app.extensions import db
        db.session.commit()
    
    # Архив пользователя (теперь "Завершенные отчеты"):
    # Сюда попадают отчеты, которые пользователь уже сдал (и не на доработке) ИЛИ которые глобально закрыты
    filled = [t for t in assigned if (t.id in filled_ids and t.id not in revision_submissions) or t.is_completed]
    # Сортируем завершенные новые сверху
    filled.sort(key=lambda x: x.id, reverse=True)
    
    # К заполнению: назначены, еще не сданные (или отправленные на доработку!) и не завершенные глобально
    unfilled = [t for t in assigned if (t.id not in filled_ids or t.id in revision_submissions) and not t.is_completed]
    
    # Сортируем невыполненные: отчеты на доработке показываем первыми!
    unfilled.sort(key=lambda x: (0 if x.id in revision_submissions else 1, x.deadline or date.max))
    
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
        matched_templates = ReportTemplate.query.filter_by(short_name=selected_short_name, is_template=False, is_published=True).order_by(ReportTemplate.id.desc()).all()
        # Оставляем только те, что назначены текущему пользователю
        matched_templates = [t for t in matched_templates if t in assigned]
        
        from app.services.stat_service import StatService
        stat_schema = StatService.build_unified_stat_schema(matched_templates, current_user.id)
                                    
    # Активные объявления для текущего пользователя
    raw_announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()
    active_announcements = [a for a in raw_announcements if a.is_visible_to_user(current_user)]

    submissions_by_template = {s.template_id: s for s in submissions}

    template_name = 'mobile/user_dashboard.html' if is_mobile(request) else 'user_dashboard.html'
    return render_template(template_name, 
                           unfilled_templates=active,
                           filled_templates=filled, 
                           attached_files=files_list,
                           stat_short_names=stat_short_names,
                           selected_short_name=selected_short_name,
                           stat_schema=stat_schema,
                           revision_submissions=revision_submissions,
                           submissions_by_template=submissions_by_template,
                           active_announcements=active_announcements,
                           current_date=date.today())


@reports_bp.route('/export_statistics', methods=['GET'])
@login_required
def export_user_statistics():
    selected_short_name = request.args.get('short_name')
    if not selected_short_name:
        return redirect(url_for('reports.dashboard', tab='statisticsTab'))

    user = current_user

    # Находим опубликованные шаблоны данного типа, назначенные этому пользователю
    templates = ReportTemplate.query.filter_by(
        short_name=selected_short_name,
        is_published=True,
        is_template=False
    ).order_by(ReportTemplate.id.desc()).all()

    assigned_templates = [
        t for t in templates
        if any(a.id == user.id for a in t.assigned_users)
    ]

    if not assigned_templates:
        return redirect(url_for('reports.dashboard', tab='statisticsTab'))

    from app.services.stat_service import StatService
    stat_schema = StatService.build_unified_stat_schema(assigned_templates, user.id)

    if not stat_schema:
        return redirect(url_for('reports.dashboard', tab='statisticsTab'))

    output, filename = ExcelService.export_statistics(stat_schema, selected_short_name, user_title=None)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@reports_bp.route('/api/calendar_events')
@login_required
def calendar_events():
    """
    Возвращает список событий (дедлайнов) для интерактивного календаря пользователя.
    """
    user = current_user
    submissions = ReportSubmission.query.filter_by(user_id=user.id).all()
    filled_ids = set([s.template_id for s in submissions if not s.is_revision])
    revision_submissions = {s.template_id: s for s in submissions if s.is_revision}
    
    # Отчеты, назначенные пользователю, опубликованные и имеющие дедлайн
    if user.role in ['admin', 'manager']:
        assigned = ReportTemplate.query.filter(ReportTemplate.is_published == True, ReportTemplate.deadline != None).all()
    else:
        assigned = [t for t in user.assigned_templates if t.is_published and t.deadline]
        
    events = []
    today = date.today()
    
    for t in assigned:
        deadline_date = t.deadline.date() if hasattr(t.deadline, 'date') else t.deadline
        deadline_str = deadline_date.strftime('%Y-%m-%d')
        deadline_formatted = deadline_date.strftime('%d.%m.%Y')
        days_left = (deadline_date - today).days
        is_rev = t.id in revision_submissions
        is_filled = t.id in filled_ids
        
        # Не показываем сданные отчеты (если они не на доработке)
        if is_filled and not is_rev:
            continue
            
        # Не показываем просроченные или завершенные отчеты (если они не на доработке)
        if (days_left < 0 or t.is_completed) and not is_rev:
            continue
        
        if is_rev:
            status = 'revision'
            status_label = 'Доработка'
            color = '#ff0072'
        elif days_left <= 3:
            status = 'urgent'
            status_label = f'Осталось {days_left} дн.' if days_left > 0 else 'Срок сегодня'
            color = '#f59e0b'
        else:
            status = 'active'
            status_label = 'В работе'
            color = '#003366'
            
        rev_sub = revision_submissions.get(t.id)
        events.append({
            'id': str(t.id),
            'title': t.short_name or t.name,
            'start': deadline_str,
            'allDay': True,
            'backgroundColor': color,
            'borderColor': color,
            'textColor': '#ffffff',
            'extendedProps': {
                'templateId': t.id,
                'name': t.name,
                'shortName': t.short_name or t.name,
                'period': t.period or 'не указан',
                'deadline': deadline_formatted,
                'daysLeft': days_left,
                'status': status,
                'statusLabel': status_label,
                'statusColor': color,
                'isRevision': is_rev,
                'revisionComment': rev_sub.revision_comment if rev_sub else None,
                'revisionDate': (rev_sub.returned_at.strftime('%d.%m.%Y %H:%M') if (rev_sub and rev_sub.returned_at) else None),
                'attachmentsCount': len(t.attachments),
                'fillUrl': url_for('reports.fill_report', template_id=t.id),
                'isLocked': bool(t.is_completed or (days_left < 0 and not is_rev))
            }
        })
        
    # Сортируем: сначала отчеты на доработке, затем ближайшие по дедлайну
    events.sort(key=lambda x: (0 if x['extendedProps']['isRevision'] else 1, x['start']))
    return jsonify(events)

