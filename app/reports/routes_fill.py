"""
Модуль отчетов: Заполнение отчетов (Reports - Fill).
Предоставляет интерфейс для ввода данных (показателей) пользователями
в соответствии со схемой шаблона. Обрабатывает AJAX-запросы на сохранение.
"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.reports import reports_bp
from app.models import ReportTemplate, ReportSubmission
from app.utils import log_action, is_mobile

# ==========================================
# ЗАПОЛНЕНИЕ ОТЧЕТОВ ПОЛЬЗОВАТЕЛЯМИ
# ==========================================

def get_historical_data(template, user_id):
    """
    Найти самую свежую submission пользователя для предыдущих шаблонов с тем же short_name.
    """
    past_templates = ReportTemplate.query.filter_by(short_name=template.short_name) \
                                         .filter(ReportTemplate.id != template.id) \
                                         .order_by(ReportTemplate.deadline.desc().nullslast(), ReportTemplate.id.desc()) \
                                         .all()
    if not past_templates:
        return {}
        
    past_template_ids = [t.id for t in past_templates]
    submissions = ReportSubmission.query.filter(
        ReportSubmission.template_id.in_(past_template_ids),
        ReportSubmission.user_id == user_id
    ).all()
    
    for t in past_templates:
        for s in submissions:
            if s.template_id == t.id and s.data:
                return s.data
    return {}

@reports_bp.route('/fill/<int:template_id>', methods=['GET', 'POST'])
@login_required
def fill_report(template_id):
    """
    Страница, где учреждение вводит свои данные (цифры и текст).
    GET: Отрисовывает форму на основе JSON-схемы шаблона.
    POST: Принимает заполненные данные в виде JSON (AJAX-запрос) и сохраняет в БД.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    if current_user.role != 'user':
        return "Доступ ограничен", 403
        
    # Пробуем найти уже существующий ответ (черновик или сданный отчет)
    submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=current_user.id).first()
    
    # Блокировка редактирования, если прошел срок сдачи
    is_locked = template.deadline and date.today() > template.deadline
    
    if not submission:
        # Если нет ответа, то проверяем строго: форма должна быть назначена и опубликована
        if template not in current_user.assigned_templates or not template.is_published:
            return "Доступ ограничен или форма не опубликована", 403
    else:
        # Если ответ есть (архивная запись), но форма больше не актуальна, просто блокируем редактирование
        if template not in current_user.assigned_templates or not template.is_published:
            is_locked = True
    
    # Сохранение данных (AJAX запрос из JS)
    if request.method == 'POST':
        if is_locked:
            return jsonify({'status': 'error', 'message': 'Дедлайн прошел. Редактирование запрещено.'}), 403
            
        if not submission:
            submission = ReportSubmission(template_id=template.id, user_id=current_user.id)
            db.session.add(submission)
        else:
            schema = template.schema or []
        old_data = submission.data or {}
        
        json_data = request.get_json()
        
        # --- СЕРВЕРНАЯ ВАЛИДАЦИЯ ---
        if type(template.schema) is str:
            import json
            try:
                schema = json.loads(template.schema)
            except:
                schema = []
        else:
            schema = template.schema or []
            
        historical_data = None
        for sheet in schema:
            for field in sheet.get('fields', []):
                if field.get('is_active') is False:
                    # Принудительно восстанавливаем старое значение и пропускаем валидацию
                    if field['name'] in old_data:
                        json_data[field['name']] = old_data[field['name']]
                    else:
                        if historical_data is None:
                            historical_data = get_historical_data(template, current_user.id)
                        if field['name'] in historical_data:
                            json_data[field['name']] = historical_data[field['name']]
                        elif field['name'] in json_data:
                            del json_data[field['name']]
                    continue
                    
                val = json_data.get(field['name'])
                
                # Приводим к списку для унифицированной проверки
                vals_to_check = val if isinstance(val, list) else [val]
                
                # 1. Проверка обязательных полей
                if field.get('required'):
                    # Должно быть хотя бы одно непустое значение
                    if not vals_to_check or all(v is None or str(v).strip() == '' for v in vals_to_check):
                        return jsonify({'status': 'error', 'message': f'Обязательное поле "{field["label"]}" не заполнено.'}), 400
                        
                # 2. Проверка типов и значений
                for v in vals_to_check:
                    if v is not None and str(v).strip() != '':
                        if field.get('type') == 'number':
                            try:
                                num_val = float(v)
                                if num_val < 0:
                                    return jsonify({'status': 'error', 'message': f'Значения в поле "{field["label"]}" не могут быть отрицательными.'}), 400
                            except ValueError:
                                return jsonify({'status': 'error', 'message': f'Значение в поле "{field["label"]}" должно быть числом.'}), 400
                        elif field.get('type') == 'text':
                            pass
                            
        # 3. Иерархическая валидация
        from app.utils import build_schema_tree
        from app.services.validation_service import validate_hierarchy
        schema_tree = build_schema_tree(schema)
        is_valid, error_msg = validate_hierarchy(schema_tree, json_data)
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400

        submission.data = json_data
        db.session.commit()
        log_action('Заполнение отчета', f'Отправлены данные для отчета {template.short_name}')
        return jsonify({'status': 'success'})
        
    # Отрисовка формы для пользователя (GET запрос)
    from app.utils import build_schema_tree
    
    schema_obj = template.schema
    if isinstance(schema_obj, str):
        import json
        try:
            schema_obj = json.loads(schema_obj)
        except:
            schema_obj = []
            
    # Подготавливаем отображаемые данные, подтягивая историю для неактивных полей
    display_data = submission.data.copy() if (submission and submission.data) else {}
    historical_data = None
    
    for sheet in schema_obj:
        for field in sheet.get('fields', []):
            if field.get('is_active') is False:
                if field['name'] not in display_data:
                    if historical_data is None:
                        historical_data = get_historical_data(template, current_user.id)
                    if field['name'] in historical_data:
                        display_data[field['name']] = historical_data[field['name']]
                        
    class DummySubmission:
        def __init__(self, data):
            self.data = data
            
    virtual_submission = DummySubmission(
        data=display_data
    )
            
    schema_tree = build_schema_tree(schema_obj)
    
    template_name = 'mobile/fill_report.html' if is_mobile(request) else 'fill_report.html'
    return render_template(template_name, template=template, schema=schema_tree, submission=virtual_submission, is_locked=is_locked)

@reports_bp.route('/fill/<int:template_id>/past_submissions', methods=['GET'])
@login_required
def get_past_submissions(template_id):
    """
    Возвращает список всех предыдущих отчетов пользователя (с тем же short_name),
    для которых есть сохраненные данные.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    if current_user.role != 'user' or template not in current_user.assigned_templates:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    # Ищем все предыдущие шаблоны с таким же short_name
    past_templates = ReportTemplate.query.filter_by(short_name=template.short_name) \
                                         .filter(ReportTemplate.id != template.id) \
                                         .order_by(ReportTemplate.deadline.desc().nullslast(), ReportTemplate.id.desc()) \
                                         .all()
                                         
    if not past_templates:
        return jsonify({'status': 'success', 'data': []})
        
    past_template_ids = [t.id for t in past_templates]
    
    # Ищем submission для этих шаблонов
    submissions = ReportSubmission.query.filter(
        ReportSubmission.template_id.in_(past_template_ids),
        ReportSubmission.user_id == current_user.id
    ).all()
    
    # Формируем результат
    sub_map = {s.template_id: s for s in submissions if s.data}
    
    result = []
    for t in past_templates:
        if t.id in sub_map:
            # Формат: [Период] Название отчета
            label = f"[{t.period if t.period else 'Без периода'}] {t.name}"
            result.append({
                'submission_id': sub_map[t.id].id,
                'label': label,
                'deadline': t.deadline.strftime('%d.%m.%Y') if t.deadline else 'Без срока'
            })
            
    return jsonify({'status': 'success', 'data': result})


@reports_bp.route('/fill/<int:template_id>/previous_data', methods=['GET'])
@login_required
def get_previous_data(template_id):
    """
    Возвращает данные из указанного submission_id (если передан) или из самого свежего предыдущего отчета.
    """
    template = ReportTemplate.query.get_or_404(template_id)
    
    if current_user.role != 'user' or template not in current_user.assigned_templates:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    submission_id = request.args.get('submission_id', type=int)
    
    if submission_id:
        prev_submission = ReportSubmission.query.get(submission_id)
        if not prev_submission or prev_submission.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Отчет не найден или нет доступа.'}), 404
        previous_template = prev_submission.template
    else:
        # Старая логика: Ищем самый свежий
        previous_template = ReportTemplate.query.filter_by(short_name=template.short_name) \
                                                .filter(ReportTemplate.id != template.id) \
                                                .order_by(ReportTemplate.deadline.desc().nullslast(), ReportTemplate.id.desc()) \
                                                .first()
        if not previous_template:
            return jsonify({'status': 'error', 'message': 'Предыдущий период для данного отчета не найден.'}), 404
            
        prev_submission = ReportSubmission.query.filter_by(template_id=previous_template.id, user_id=current_user.id).first()
    
    if not prev_submission or not prev_submission.data:
        return jsonify({'status': 'error', 'message': 'Данные для выбранного отчета не найдены.'}), 404
        
    import re
    def normalize_label(label):
        if not label: return ''
        return re.sub(r'\W+', '', str(label)).lower()

    def get_schema(t):
        if type(t.schema) is str:
            import json
            try:
                return json.loads(t.schema)
            except:
                return []
        return t.schema or []
        
    old_schema = get_schema(previous_template)
    new_schema = get_schema(template)
    
    def build_path_mapping(schema):
        mapping = {}
        for sheet in schema:
            stack = []
            for field in sheet.get('fields', []):
                level = int(field.get('level', 0))
                norm = normalize_label(field.get('label', ''))
                
                while stack and stack[-1]['level'] >= level:
                    stack.pop()
                    
                path = '/'.join([s['norm'] for s in stack] + [norm])
                
                # Если такой путь уже есть (одинаковые поля на одном уровне), добавляем индекс
                original_path = path
                counter = 1
                while path in mapping.values():
                    path = f"{original_path}_{counter}"
                    counter += 1
                
                mapping[field['name']] = path
                stack.append({'level': level, 'norm': norm})
        return mapping

    old_name_to_path = build_path_mapping(old_schema)
    new_name_to_path = build_path_mapping(new_schema)
    path_to_new_name = {path: name for name, path in new_name_to_path.items()}
    
    # 3. Translate old data to new data
    mapped_data = {}
    for old_name, value in prev_submission.data.items():
        if old_name in old_name_to_path:
            path = old_name_to_path[old_name]
            if path in path_to_new_name:
                new_name = path_to_new_name[path]
                mapped_data[new_name] = value
        else:
            # If field wasn't in schema (e.g. meta field), just pass it along just in case
            mapped_data[old_name] = value
            
    return jsonify({
        'status': 'success',
        'data': mapped_data,
        'message': f'Данные из отчета "{previous_template.period or previous_template.name}" успешно загружены.'
    })