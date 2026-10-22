"""

Модуль отчетов: Просмотр и Экспорт данных (Reports - Data).

Предоставляет функционал для администраторов:

- Просмотр сводной HTML-таблицы (все ответы учреждений по одному отчету).

- Встроенное (inline) редактирование ответов прямо в браузере.

- Экспорт всех заполненных данных в сводный Excel файл (.xlsx) с форматированием.

"""

from flask import render_template, send_file, request, jsonify

from flask_login import login_required, current_user

from io import BytesIO

import openpyxl

from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from openpyxl.utils import get_column_letter

import re

from app.reports import reports_bp

from app.models import ReportTemplate, ReportSubmission, User, ReportDraft

from app.extensions import db

from datetime import datetime
from app.utils import log_action



# ==========================================

# ПРОСМОТР И ЭКСПОРТ ДАННЫХ

# ==========================================




def get_sort_key(x):
    """Универсальный ключ сортировки для сданных отчетов и ручных строк."""
    if not getattr(x, 'user', None):
        return (2, 0)
    uid = getattr(x.user, 'id', None)
    if isinstance(uid, int):
        return (0, uid)
    return (1, getattr(x, 'manual_row_id', 0) or 0)


class ManualRowAdapter:
    """Адаптер ручной строки для сводной таблицы."""
    def __init__(self, row):
        self.manual_row = row
        self.manual_row_id = row.id
        self.is_manual = True
        self.id = None
        self.is_revision = False
        self.revision_comment = None
        self.data = row.data or {}
        self.org_name = row.org_name
        self.subgroup = (row.subgroup or '').strip()
        self.created_by = row.created_by
        self.created_at = row.created_at
        self.updated_by = row.updated_by
        self.updated_at = row.updated_at
        
        class UserProxy:
            def __init__(self, desc, sg, row_id):
                self.id = f"m_{row_id}"
                self.description = desc
                self.username = desc
                self.subgroup = sg
                self.group = None
        self.user = UserProxy(row.org_name, self.subgroup, row.id)

def build_sheet_blocks(sheet, submissions):

    """

    Разбивает ответы организаций для конкретного листа отчета на структурированные блоки:

    - именованные подгруппы (type: 'subgroup') со списками учреждений и предварительно рассчитанными суммами

    - общий список организаций без подгруппы (type: 'general')

    """

    import hashlib



    t_groups = sheet.get('target_groups', [])

    old_group = sheet.get('target_group')

    all_t_groups = list(t_groups) + ([old_group] if old_group and old_group not in t_groups else [])



    sheet_subs = []

    for sub in submissions:

        user = getattr(sub, 'user', None)

        if not user:

            continue

        user_group = getattr(user, 'group', None)

        if not all_t_groups or (user_group and user_group in all_t_groups):

            sheet_subs.append(sub)



    # Сортируем учреждения листа строго по порядку списка пользователей

    sheet_subs.sort(key=get_sort_key)



    leaf_fields = sheet.get('leaf_fields', [])

    numeric_field_names = [

        f.get('name') for f in leaf_fields

        if str(f.get('type', '')).lower() in ['number', 'числовое']

    ]



    blocks = []

    processed_subgroups = set()

    current_general_chunk = []

    subgroup_counter = 0



    for sub in sheet_subs:

        sg = (getattr(sub.user, 'subgroup', None) or getattr(sub, 'subgroup', None) or '').strip() if (getattr(sub, 'user', None) or getattr(sub, 'subgroup', None)) else ''

        

        if not sg:

            # Организация без подгруппы — накапливаем в текущий общий блок

            current_general_chunk.append(sub)

        else:

            if sg in processed_subgroups:

                # Подгруппа уже выведена при первом появлении её участника

                continue



            # Сбрасываем накопленные организации без подгруппы

            if current_general_chunk:

                blocks.append({

                    'type': 'general',

                    'submissions': current_general_chunk

                })

                current_general_chunk = []



            # Собираем всех участников этой подгруппы в порядке списка пользователей

            sg_subs = [

                s for s in sheet_subs

                if (getattr(s.user, 'subgroup', None) or getattr(s, 'subgroup', None) or '').strip() == sg

            ]

            sg_subs.sort(key=get_sort_key)



            totals = {fname: 0.0 for fname in numeric_field_names}

            has_subtotals = {fname: False for fname in numeric_field_names}



            for s in sg_subs:

                sub_data = getattr(s, 'data', {}) or {}

                for fname in numeric_field_names:

                    val = sub_data.get(fname)

                    if val is not None and val != '':

                        if isinstance(val, list):

                            for v in val:

                                if v is not None and v != '':

                                    try:

                                        totals[fname] += float(v)

                                        has_subtotals[fname] = True

                                    except (ValueError, TypeError):

                                        pass

                        else:

                            try:

                                totals[fname] += float(val)

                                has_subtotals[fname] = True

                            except (ValueError, TypeError):

                                pass



            formatted_totals = {}

            for fname in numeric_field_names:

                if has_subtotals[fname]:

                    val = totals[fname]

                    formatted_totals[fname] = int(val) if val.is_integer() else round(val, 2)

                else:

                    formatted_totals[fname] = 0



            subgroup_counter += 1

            sg_id = f"sg_{subgroup_counter}_{hashlib.md5(sg.encode('utf-8')).hexdigest()[:8]}"

            blocks.append({

                'type': 'subgroup',

                'subgroup_name': sg,

                'subgroup_id': sg_id,

                'submissions': sg_subs,

                'totals': formatted_totals

            })

            processed_subgroups.add(sg)



    # Добавляем оставшиеся организации без подгруппы в конце

    if current_general_chunk:

        blocks.append({

            'type': 'general',

            'submissions': current_general_chunk

        })



    return blocks





@reports_bp.route('/view_data/<int:template_id>')

@login_required

def view_data(template_id):

    """

    Просмотр сводных данных по отчету прямо в браузере (HTML таблица).

    Каждый лист шаблона отображается отдельной вкладкой, столбцы - это поля, 

    строки - это ответившие учреждения.

    """

    if current_user.role not in ['admin', 'manager']:

        return "Доступ ограничен", 403

        

    template = ReportTemplate.query.get_or_404(template_id)

    

    # Получаем все сданные ответы по данному шаблону
    submissions = ReportSubmission.query.filter_by(template_id=template_id).all()

    # Загружаем ручные строки для сводной таблицы
    from app.models import ManualRow
    manual_rows = ManualRow.query.filter_by(template_id=template_id).all()
    for mr in manual_rows:
        submissions.append(ManualRowAdapter(mr))

    # Сортируем ответы по порядку учреждений в списке пользователей (User.id)
    submissions.sort(key=get_sort_key)

    

    from app.utils import build_table_headers

    from app.reports.routes_fill import get_historical_data

    

    has_inactive_fields = False

    inactive_field_names = []

    

    # Обогащаем схему шаблона данными для сложной шапки

    for sheet in template.schema:

        fields = sheet.get('fields', [])

        header_rows, leaf_fields = build_table_headers(fields)

        sheet['header_rows'] = header_rows

        sheet['leaf_fields'] = leaf_fields

        for field in leaf_fields:

            if field.get('is_active') is False:

                has_inactive_fields = True

                field_name = field.get('name')

                if field_name:

                    inactive_field_names.append(field_name)



    if has_inactive_fields:

        submitted_user_ids = {s.user_id for s in submissions}

        unsubmitted_users = [u for u in template.assigned_users if u.id not in submitted_user_ids]

        

        class DummySubmission:

            def __init__(self, user, data):

                self.user = user

                self.data = data

                self.id = None

                self.is_revision = False

                self.revision_comment = None

                

        for user in unsubmitted_users:

            hist_data = get_historical_data(template, user.id)

            if hist_data:

                dummy_data = {}

                for fname in inactive_field_names:

                    if fname in hist_data:

                        dummy_data[fname] = hist_data[fname]

                submissions.append(DummySubmission(user=user, data=dummy_data))

        

        # Повторно упорядочиваем с учетом добавленных учреждений

        submissions.sort(key=get_sort_key)



    # Раскладываем данные каждого листа по блокам (подгруппы и общий список)

    for sheet in template.schema:

        sheet['blocks'] = build_sheet_blocks(sheet, submissions)



    # Экспресс-статистика по шаблону
    if hasattr(template.assigned_users, 'count'):
        assigned_count = template.assigned_users.count()
    elif template.assigned_users:
        assigned_count = len(template.assigned_users)
    else:
        assigned_count = 0
    real_subs_count = len([s for s in submissions if not getattr(s, 'is_manual', False)])
    total_assigned = max(assigned_count, real_subs_count)

    submitted_user_ids = {
        getattr(s, 'user_id', None) or (s.user.id if getattr(s, 'user', None) else None)
        for s in submissions 
        if getattr(s, 'id', None) and not getattr(s, 'is_revision', False)
    }
    submitted_user_ids.discard(None)
    submitted_count = len(submitted_user_ids)

    revision_user_ids = {
        getattr(s, 'user_id', None) or (s.user.id if getattr(s, 'user', None) else None)
        for s in submissions 
        if getattr(s, 'is_revision', False)
    }
    revision_user_ids.discard(None)
    revision_count = len(revision_user_ids)

    stats = {
        'total': total_assigned,
        'submitted': submitted_count,
        'revision': revision_count
    }

    existing_subgroups = set()
    for u in User.query.filter(User.subgroup.isnot(None)).all():
        if u.subgroup and u.subgroup.strip():
            existing_subgroups.add(u.subgroup.strip())
    for mr in manual_rows:
        if mr.subgroup and mr.subgroup.strip():
            existing_subgroups.add(mr.subgroup.strip())
    existing_subgroups = sorted(list(existing_subgroups))

    return render_template('report_data_view.html', template=template, submissions=submissions, stats=stats, existing_subgroups=existing_subgroups)



@reports_bp.route('/inline_update/<int:template_id>', methods=['POST'])

@login_required

def inline_update(template_id):

    """

    Сохранение изменений напрямую из сводной таблицы (inline editing).

    Принимает JSON с изменениями (список словарей или один словарь) и обновляет поле `data`.

    """

    if current_user.role not in ['admin', 'manager']:

        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

        

    template = ReportTemplate.query.get_or_404(template_id)

    req = request.get_json()

    

    updates = req if isinstance(req, list) else [req]

    

    for item in updates:
        user_id = item.get('user_id')
        manual_row_id = item.get('manual_row_id')
        field_name = item.get('field_name')
        value = item.get('value')

        if (not user_id and not manual_row_id) or not field_name:
            continue



        # --- ВАЛИДАЦИЯ ПО СХЕМЕ ШАБЛОНА ---

        # Находим описание поля в схеме, чтобы применить те же правила, что и при обычном сохранении

        import json as _json

        schema = template.schema if not isinstance(template.schema, str) else _json.loads(template.schema or '[]')

        field_def = next(

            (f for sheet in (schema or []) for f in sheet.get('fields', []) if f['name'] == field_name),

            None

        )

        if field_def and value is not None and str(value).strip() != '':

            if field_def.get('is_multiple'):

                if isinstance(value, str):

                    value = [v.strip() for v in value.split('\n') if v.strip()]

                    

            if field_def.get('type') == 'number':

                try:

                    # If it's multiple, we should probably check each, but inline_update only checks scalar currently. Let's adapt:

                    vals_to_check = value if isinstance(value, list) else [value]

                    for v in vals_to_check:

                        num_val = float(v)

                        if num_val < 0:

                            return jsonify({'status': 'error', 'message': f'Поле "{field_def["label"]}" не может быть отрицательным.'}), 400

                except (ValueError, TypeError):

                    return jsonify({'status': 'error', 'message': f'Поле "{field_def["label"]}" должно быть числом.'}), 400

            elif field_def.get('type') == 'text':

                pass

        # -----------------------------------



        if manual_row_id:
            from app.models import ManualRow
            mr = ManualRow.query.filter_by(id=manual_row_id, template_id=template_id).first()
            if mr:
                data_copy = mr.data.copy() if mr.data else {}
                data_copy[field_name] = value
                mr.data = data_copy
                mr.updated_by_id = current_user.id
                mr.updated_at = datetime.utcnow()
            continue

        submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=user_id).first()

        

        if not submission:

            submission = ReportSubmission(template_id=template.id, user_id=user_id, data={})

            db.session.add(submission)

            

        # ВАЖНО: Для корректного обнаружения изменений в JSON/JSONB колонках SQLAlchemy

        # необходимо создать новую копию словаря `data`, изменить её и присвоить обратно.

        data_copy = submission.data.copy() if submission.data else {}

        data_copy[field_name] = value

        submission.data = data_copy

    

    db.session.commit()

    log_action('Редактирование данных отчета', f'Внесены изменения в сводной таблице отчета {template.short_name}')

    return jsonify({'status': 'success'})





@reports_bp.route('/export_excel/<int:template_id>')

@login_required

def export_excel(template_id):

    if current_user.role not in ['admin', 'manager']:

        return "Доступ ограничен", 403

        

    from app.services.task_service import TaskService

    task_id = TaskService.start_excel_generation(template_id, current_user.id)

    return jsonify({'status': 'success', 'task_id': task_id})





@reports_bp.route('/export_multi_excel', methods=['POST'])

@login_required

def export_multi_excel():

    """

    Запуск фоновой генерации единого сводного Excel файла для нескольких выбранных отчетов.

    Доступно только для ролей admin и manager.

    Разрешено выгружать ТОЛЬКО завершенные отчеты.

    """

    if current_user.role not in ['admin', 'manager']:

        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403



    data = request.get_json() or {}

    template_ids = data.get('template_ids', [])

    include_toc = bool(data.get('include_toc', True))



    if not template_ids or not isinstance(template_ids, list):

        return jsonify({'status': 'error', 'message': 'Не выбраны отчеты для выгрузки'}), 400



    try:

        template_ids = [int(tid) for tid in template_ids]

    except (ValueError, TypeError):

        return jsonify({'status': 'error', 'message': 'Некорректный формат идентификаторов'}), 400



    # 1. Получаем доступные отчеты в зависимости от роли

    if current_user.role == 'manager':

        from app.utils import get_manager_department

        dept = get_manager_department(current_user)

        if dept:

            all_templates = dept.templates.all()

        else:

            all_templates = []

    else:

        all_templates = ReportTemplate.query.all()



    # 2. Определяем завершенные отчеты (строгое требование: только завершенные отчеты)

    from app.services.template_service import TemplateService

    _, _, _, _, _, _, _, completed_templates, *_ = TemplateService.get_dashboard_stats(all_templates)

    completed_ids = {t.id for t in completed_templates}



    # Проверяем, что ВСЕ запрошенные отчеты завершены и доступны пользователю

    invalid_ids = [tid for tid in template_ids if tid not in completed_ids]

    if invalid_ids:

        return jsonify({

            'status': 'error',

            'message': 'Для пакетной выгрузки доступны только завершенные отчеты'

        }), 400



    from app.services.task_service import TaskService

    task_id = TaskService.start_multi_excel_generation(

        template_ids=template_ids,

        current_user_id=current_user.id,

        include_toc=include_toc

    )



    log_action('Пакетный экспорт в Excel', f'Запущена выгрузка {len(template_ids)} завершенных отчетов')



    return jsonify({'status': 'success', 'task_id': task_id})







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





@reports_bp.route('/return_revision/<int:template_id>/<int:user_id>', methods=['POST'])

@login_required

def return_revision(template_id, user_id):

    """

    Возврат отчета на доработку.

    Запись ReportSubmission НЕ удаляется, а помечается флагом is_revision=True и сохраняет комментарий куратора.

    """

    from datetime import datetime



    if current_user.role not in ['admin', 'manager']:

        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

        

    template = ReportTemplate.query.get_or_404(template_id)

    submission = ReportSubmission.query.filter_by(template_id=template_id, user_id=user_id).first()

    

    if not submission:

        return jsonify({'status': 'error', 'message': 'Сданный отчет не найден'}), 404

        

    req_data = request.get_json(silent=True) or {}

    comment = req_data.get('comment', '').strip()

    if not comment:

        return jsonify({'status': 'error', 'message': 'Необходимо указать причину возврата на доработку'}), 400



    submission.is_revision = True

    submission.revision_comment = comment

    submission.returned_at = datetime.utcnow()

    submission.returned_by_id = current_user.id

    

    target_user = User.query.get(user_id)

    org_name = target_user.description or target_user.username if target_user else str(user_id)

    

    log_action('Возврат отчета на доработку', f'Отчет "{template.short_name}" возвращен учреждению {org_name}. Замечание: {comment}')

    

    db.session.commit()

    

    return jsonify({'status': 'success', 'message': 'Отчет возвращен на доработку'})





@reports_bp.route('/delete_submission/<int:template_id>/<int:user_id>', methods=['POST'])

@login_required

def delete_submission(template_id, user_id):

    """

    Безвозвратное удаление сданного отчета пользователя. Доступно только администраторам.

    """

    if current_user.role != 'admin':

        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

        

    template = ReportTemplate.query.get_or_404(template_id)

    submissions = ReportSubmission.query.filter_by(template_id=template_id, user_id=user_id).all()

    

    if not submissions:

        return jsonify({'status': 'error', 'message': 'Сданный отчет не найден'}), 404

        

    # Удаляем все связанные черновики, если они существуют

    from app.models import ReportDraft

    drafts = ReportDraft.query.filter_by(template_id=template_id, user_id=user_id).all()

    for draft in drafts:

        db.session.delete(draft)

        

    # Удаляем все записи сдачи

    for sub in submissions:

        db.session.delete(sub)

    

    target_user = User.query.get(user_id)

    org_name = target_user.description or target_user.username if target_user else str(user_id)

    

    log_action('Удаление данных отчета', f'Безвозвратно удалены данные учреждения {org_name} из отчета "{template.short_name}"')

    

    db.session.commit()

    

    return jsonify({'status': 'success', 'message': 'Данные отчета успешно удалены'})


@reports_bp.route('/preview_summary_import/<int:template_id>', methods=['POST'])
@login_required
def preview_summary_import(template_id):
    """
    Предпросмотр импорта сводной таблицы Excel.
    Принимает .xlsx файл, сопоставляет данные с базой и возвращает список различий (diff).
    Изменения в базу данных на этом этапе НЕ сохраняются.
    """
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or template.department_id != dept.id:
            return jsonify({'status': 'error', 'message': 'У вас нет доступа к этому отчету'}), 403

    file = request.files.get('file')
    if not file:
        return jsonify({'status': 'error', 'message': 'Файл не выбран'}), 400

    filename = (file.filename or '').lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xlsm')):
        return jsonify({'status': 'error', 'message': 'Поддерживаются только файлы формата .xlsx'}), 400

    from app.services.excel_service import ExcelService
    result = ExcelService.parse_summary_excel(file, template)
    if not result.get('success'):
        return jsonify({'status': 'error', 'message': result.get('error', 'Ошибка чтения файла')}), 400

    return jsonify({
        'status': 'success',
        'diffs': result['diffs'],
        'total_changes': result['total_changes'],
        'changed_orgs_count': result['changed_orgs_count'],
        'total_orgs_found': result['total_orgs_found'],
        'warnings': result['warnings']
    })


@reports_bp.route('/apply_summary_import/<int:template_id>', methods=['POST'])
@login_required
def apply_summary_import(template_id):
    """
    Применение подтвержденных изменений из предпросмотра сводного Excel-файла.
    Атомарно сохраняет все переданные diffs в ReportSubmission и фиксирует действие в журнале аудита.
    """
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or template.department_id != dept.id:
            return jsonify({'status': 'error', 'message': 'У вас нет доступа к этому отчету'}), 403

    req_data = request.get_json(silent=True) or {}
    diffs = req_data.get('diffs', [])
    if not diffs or not isinstance(diffs, list):
        return jsonify({'status': 'error', 'message': 'Нет данных для применения'}), 400

    from app.services.excel_service import ExcelService
    try:
        changes_count, orgs_count = ExcelService.apply_summary_changes(template, diffs)
        log_action(
            'Импорт сводного Excel',
            f'В отчете "{template.short_name}" успешно обновлено {changes_count} показателей у {orgs_count} учреждений.'
        )
        return jsonify({
            'status': 'success',
            'message': f'Успешно обновлено {changes_count} показателей у {orgs_count} учреждений.',
            'changes_count': changes_count,
            'orgs_count': orgs_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Ошибка сохранения в базу данных: {str(e)}'}), 500

@reports_bp.route('/manual_row/<int:template_id>', methods=['POST'])
@login_required
def add_manual_row(template_id):
    """Добавление ручной строки в сводную таблицу (для незарегистрированных организаций)."""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or template.department_id != dept.id:
            return jsonify({'status': 'error', 'message': 'У вас нет доступа к этому отчету'}), 403

    req_data = request.get_json(silent=True) or {}
    org_name = (req_data.get('org_name') or '').strip()
    if not org_name:
        return jsonify({'status': 'error', 'message': 'Укажите название организации'}), 400

    subgroup = (req_data.get('subgroup') or '').strip() or None
    row_data = req_data.get('data') or {}

    from app.models import ManualRow
    new_row = ManualRow(
        template_id=template_id,
        org_name=org_name,
        subgroup=subgroup,
        data=row_data,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    db.session.add(new_row)
    db.session.commit()

    # log_action imported at top
    log_action(
        'Добавление строки в сводную таблицу',
        f'В отчет "{template.short_name}" вручную добавлена строка организации "{org_name}"' + (f' (подгруппа: {subgroup})' if subgroup else '')
    )

    return jsonify({'status': 'success', 'message': 'Строка успешно добавлена', 'row_id': new_row.id})


@reports_bp.route('/manual_row/<int:template_id>/<int:row_id>', methods=['POST', 'PUT'])
@login_required
def update_manual_row(template_id, row_id):
    """Редактирование ручной строки в сводной таблице."""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or template.department_id != dept.id:
            return jsonify({'status': 'error', 'message': 'У вас нет доступа к этому отчету'}), 403

    from app.models import ManualRow
    manual_row = ManualRow.query.filter_by(id=row_id, template_id=template_id).first_or_404()

    req_data = request.get_json(silent=True) or {}
    if 'org_name' in req_data:
        org_name = (req_data.get('org_name') or '').strip()
        if not org_name:
            return jsonify({'status': 'error', 'message': 'Название организации не может быть пустым'}), 400
        manual_row.org_name = org_name

    if 'subgroup' in req_data:
        manual_row.subgroup = (req_data.get('subgroup') or '').strip() or None

    if 'data' in req_data:
        manual_row.data = req_data['data'] or {}

    manual_row.updated_by_id = current_user.id
    manual_row.updated_at = datetime.utcnow()
    db.session.commit()

    # log_action imported at top
    log_action(
        'Редактирование строки в сводной таблице',
        f'В отчете "{template.short_name}" обновлена строка организации "{manual_row.org_name}"'
    )

    return jsonify({'status': 'success', 'message': 'Строка успешно обновлена'})


@reports_bp.route('/manual_row_delete/<int:template_id>/<int:row_id>', methods=['POST', 'DELETE'])
@login_required
def delete_manual_row(template_id, row_id):
    """Удаление ручной строки из сводной таблицы."""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    template = ReportTemplate.query.get_or_404(template_id)
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or template.department_id != dept.id:
            return jsonify({'status': 'error', 'message': 'У вас нет доступа к этому отчету'}), 403

    from app.models import ManualRow
    manual_row = ManualRow.query.filter_by(id=row_id, template_id=template_id).first_or_404()
    org_name = manual_row.org_name

    db.session.delete(manual_row)
    db.session.commit()

    # log_action imported at top
    log_action(
        'Удаление строки из сводной таблицы',
        f'Из отчета "{template.short_name}" удалена строка организации "{org_name}"'
    )

    return jsonify({'status': 'success', 'message': 'Строка успешно удалена'})

