from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import Dictionary, User
from app import db
from app.utils import log_action



@admin_bp.route('/dictionaries/add', methods=['POST'])
@login_required
def add_dictionary():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    name = request.form.get('name')
    items_raw = request.form.get('items', '')
    
    if not name or not items_raw:
        flash('Необходимо заполнить название и хотя бы один вариант.', 'danger')
        return redirect(url_for('admin.dashboard') + '#listsTab')
        
    # Разделяем по переносам строк, удаляем пустые и лишние пробелы
    items = [line.strip() for line in items_raw.replace('\r', '').split('\n') if line.strip()]
    
    if not items:
        flash('Список вариантов пуст.', 'danger')
        return redirect(url_for('admin.dashboard') + '#listsTab')
        
    new_dict = Dictionary(name=name, items=items)
    db.session.add(new_dict)
    db.session.commit()
    
    log_action('Создание шаблона', f'Создан новый шаблон выпадающего списка: {name}')
    flash('Шаблон успешно создан!', 'success')
    return redirect(url_for('admin.dashboard') + '#listsTab')

@admin_bp.route('/dictionaries/<int:dict_id>/edit', methods=['POST'])
@login_required
def edit_dictionary(dict_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    dictionary = Dictionary.query.get_or_404(dict_id)
    
    name = request.form.get('name')
    items_raw = request.form.get('items', '')
    
    if not name or not items_raw:
        flash('Необходимо заполнить название и варианты.', 'danger')
        return redirect(url_for('admin.dashboard') + '#listsTab')
        
    items_list = [line.strip() for line in items_raw.replace('\r', '').split('\n') if line.strip()]
    
    dictionary.name = name
    dictionary.items = items_list
    
    # Каскадное обновление: обновляем снапшоты списков во всех существующих отчетах
    from app.models import ReportTemplate
    from sqlalchemy.orm.attributes import flag_modified
    import json
    
    templates = ReportTemplate.query.all()
    for template in templates:
        if not template.schema:
            continue
            
        schema = template.schema
        is_string = False
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
                is_string = True
            except:
                continue
                
        modified = False
        if isinstance(schema, list):
            for sheet in schema:
                for field in sheet.get('fields', []):
                    if field.get('dictionary_id') == dict_id:
                        field['options'] = items_list
                        field['dictionary_name'] = name
                        modified = True
                        
        if modified:
            if is_string:
                template.schema = json.dumps(schema, ensure_ascii=False)
            else:
                template.schema = schema
                flag_modified(template, 'schema')
                
    db.session.commit()
    
    log_action('Редактирование шаблона', f'Отредактирован шаблон выпадающего списка: {name} с обновлением во всех отчетах')
    flash('Шаблон успешно обновлен! Все отчеты, использующие этот список, также были обновлены.', 'success')
    return redirect(url_for('admin.dashboard') + '#listsTab')

@admin_bp.route('/dictionaries/<int:dict_id>/delete', methods=['POST'])
@login_required
def delete_dictionary(dict_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    dictionary = Dictionary.query.get_or_404(dict_id)
    try:
        name = dictionary.name
        db.session.delete(dictionary)
        db.session.commit()
        
        log_action('Удаление шаблона', f'Удален шаблон выпадающего списка: {name}')
        flash('Шаблон успешно удален.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении шаблона. Возможно, он используется в существующих отчетах.', 'danger')
        
    return redirect(url_for('admin.dashboard') + '#listsTab')

@admin_bp.route('/dictionaries/api/list', methods=['GET'])
@login_required
def api_get_dictionaries():
    """API для конструктора шаблонов: возвращает список справочников."""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403
        
    dictionaries = Dictionary.query.order_by(Dictionary.name).all()
    result = [{'id': d.id, 'name': d.name, 'items': d.items} for d in dictionaries]
    return jsonify({'status': 'success', 'dictionaries': result})
