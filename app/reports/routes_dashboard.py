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
    
    # Архив пользователя: собираем сами шаблоны из отправленных данных
    filled = [s.template for s in submissions if s.template is not None]
    
    # Активные отчеты: назначенные, опубликованные и еще не сданные
    assigned = [t for t in current_user.assigned_templates if t.is_published]
    unfilled = [t for t in assigned if t.id not in filled_ids]
    
    # Сортируем невыполненные по дедлайну (сначала те, что нужно сдать раньше)
    unfilled.sort(key=lambda x: x.deadline or date.max)
    
    overdue = []
    active = []
    
    for t in unfilled:
        if t.deadline and t.deadline < date.today():
            overdue.append(t)
        else:
            active.append(t)
    
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
    
    template_name = 'mobile/user_dashboard.html' if is_mobile(request) else 'user_dashboard.html'
    return render_template(template_name, 
                           unfilled_templates=active,
                           overdue_templates=overdue,
                           filled_templates=filled, 
                           attached_files=files_list,
                           current_date=date.today())

@reports_bp.route('/api/my_analytics/reports')
@login_required
def api_my_analytics_reports():
    if current_user.role != 'user':
        return jsonify({'status': 'error', 'message': 'Только для пользователей'}), 403
        
    submissions = ReportSubmission.query.filter_by(user_id=current_user.id).all()
    # Получаем уникальные short_name из шаблонов сданных отчетов
    report_names = set()
    for s in submissions:
        if s.template and s.template.short_name:
            report_names.add(s.template.short_name)
            
    return jsonify({
        'status': 'success',
        'reports': sorted(list(report_names))
    })

@reports_bp.route('/api/my_analytics/data/<path:short_name>')
@login_required
def api_my_analytics_data(short_name):
    if current_user.role != 'user':
        return jsonify({'status': 'error', 'message': 'Только для пользователей'}), 403
        
    # Ищем все шаблоны с таким short_name
    templates = ReportTemplate.query.filter_by(short_name=short_name).all()
    template_ids = [t.id for t in templates]
    
    # Ищем все ответы этого пользователя по этим шаблонам
    submissions = ReportSubmission.query.filter(
        ReportSubmission.user_id == current_user.id,
        ReportSubmission.template_id.in_(template_ids)
    ).all()
    
    # Сортируем сдачи по дедлайну шаблона
    submissions.sort(key=lambda s: (s.template.deadline or date.min, s.template.id))
    
    periods = []
    datasets = {}
    
    if not submissions:
        return jsonify({'status': 'success', 'periods': [], 'datasets': {}})
        
    latest_template = submissions[-1].template
    
    def get_schema(t):
        if type(t.schema) is str:
            import json
            try: return json.loads(t.schema)
            except: return []
        return t.schema or []
        
    schema = get_schema(latest_template)
    numeric_fields = {} # name -> label
    for sheet in schema:
        for field in sheet.get('fields', []):
            if field.get('type') == 'number':
                # Используем label как имя графика
                label = field.get('label') or field.get('name')
                numeric_fields[field['name']] = label
                datasets[label] = [] # Инициализируем пустой список для каждого поля
                
    for sub in submissions:
        period_name = sub.template.period or sub.template.name
        periods.append(period_name)
        
        data = sub.data or {}
        for field_name, label in numeric_fields.items():
            val = data.get(field_name, 0)
            try:
                # Пытаемся привести к числу
                num = float(val) if val else 0
            except ValueError:
                num = 0
            datasets[label].append(num)
            
    # Убираем поля, где все значения = 0, чтобы не засорять графики
    filtered_datasets = {}
    for label, values in datasets.items():
        if any(v > 0 for v in values):
            filtered_datasets[label] = values
            
    return jsonify({
        'status': 'success',
        'periods': periods,
        'datasets': filtered_datasets
    })