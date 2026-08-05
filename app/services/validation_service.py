def sum_field_values(val):
    if val is None:
        return 0.0
    if isinstance(val, list):
        total = 0.0
        for v in val:
            if v is not None and str(v).strip() != '':
                try:
                    total += float(v)
                except ValueError:
                    pass
        return total
    else:
        if str(val).strip() != '':
            try:
                return float(val)
            except ValueError:
                pass
    return 0.0

def validate_hierarchy(schema_tree, json_data):
    """
    Рекурсивно проверяет, что сумма дочерних полей не превышает значение родительского поля.
    :param schema_tree: Дерево схемы (список листов, внутри которых fields_tree)
    :param json_data: Словарь с введенными данными
    :return: (is_valid, error_message)
    """
    for sheet in schema_tree:
        tree = sheet.get('fields_tree', [])
        is_valid, error_msg = _validate_nodes(tree, json_data)
        if not is_valid:
            return False, error_msg
    return True, ""

def _validate_nodes(nodes, json_data):
    for node in nodes:
        field = node.get('field', {})
        children = node.get('children', [])
        
        # Рекурсивно проверяем детей сначала
        is_valid, error_msg = _validate_nodes(children, json_data)
        if not is_valid:
            return False, error_msg
            
        # Проверяем сам узел
        if not children:
            continue
            
        # Пропускаем узлы-группы и текстовые узлы, а также если валидация отключена
        if field.get('type') in ('text', 'Текстовое', 'select') or field.get('validateSum') is False:
            continue
            
        parent_val_raw = json_data.get(field['name'])
        # Если родитель вообще не заполнен, пропускаем проверку
        if parent_val_raw is None or (isinstance(parent_val_raw, list) and len(parent_val_raw) == 0) or str(parent_val_raw).strip() == '':
            continue
            
        parent_sum = sum_field_values(parent_val_raw)
        
        children_sum = 0.0
        for child in children:
            child_field = child.get('field', {})
            # Суммируем только числовые дочерние поля
            if child_field.get('type') not in ('text', 'Текстовое', 'select'):
                child_val = json_data.get(child_field['name'])
                children_sum += sum_field_values(child_val)
                
        # Если сумма детей больше родителя (с учетом небольшой погрешности float)
        if children_sum > parent_sum + 0.0001:
            label = field.get('label', 'Без названия')
            return False, f'Сумма значений вложенных полей превышает значение родительского поля «{label}».'
            
    return True, ""
