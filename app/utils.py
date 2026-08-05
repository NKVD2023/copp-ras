"""
Вспомогательные утилиты приложения (Core).
Содержит функции, которые могут использоваться во всех модулях системы.
"""
from flask_login import current_user
from flask import request
from app import db
from app.models import ActionLog

def log_action(action: str, details: str = ""):
    """
    Утилита для логирования действий пользователей (аудит).
    Привязывает действие к текущему авторизованному пользователю, если он есть,
    или помечает как системное действие, если пользователя нет в контексте.

    :param action: Краткое описание действия (например, 'Вход', 'Удаление').
    :param details: Подробности (например, 'Пользователь admin удалил отчет #5').
    """
    # Получаем ID пользователя, только если контекст авторизации существует
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    ip = None
    try:
        # Пытаемся получить IP-адрес (с учетом того, что сервер может быть за прокси)
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
    except Exception:
        pass # Игнорируем ошибку, если функция вызвана вне контекста запроса (например, в фоне)

    log_entry = ActionLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка логирования: {e}")

def is_mobile(req) -> bool:
    """
    Проверяет, является ли устройство мобильным на основе заголовка User-Agent.
    """
    user_agent = req.headers.get('User-Agent', '').lower()
    mobile_patterns = [
        'android', 'webos', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'mobile'
    ]
    return any(pattern in user_agent for pattern in mobile_patterns)

def build_schema_tree(schema):
    """
    Преобразует схему отчета, заменяя плоский список полей 'fields' на древовидную структуру 'fields_tree'.
    Возвращает глубокую копию схемы.
    """
    import copy
    new_schema = copy.deepcopy(schema)
    for sheet in new_schema:
        fields = sheet.get('fields', [])
        tree = []
        stack = []
        
        for field in fields:
            level = int(field.get('level', 0))
            node = {'field': field, 'children': []}
            
            while stack and stack[-1]['level'] >= level:
                stack.pop()
                
            if not stack:
                tree.append(node)
            else:
                stack[-1]['node']['children'].append(node)
                
            stack.append({'level': level, 'node': node})
            
        sheet['fields_tree'] = tree
    return new_schema

def build_table_headers(fields):
    """
    Строит структуру сложной шапки таблицы и список листовых колонок.
    Для узлов-родителей добавляется колонка 'Всего', чтобы вывести их собственное значение.
    """
    tree = []
    stack = []
    
    # Build Tree
    for f in fields:
        level = int(f.get('level', 0))
        node = {'field': f, 'children': []}
        
        while stack and stack[-1]['level'] >= level:
            stack.pop()
            
        if not stack:
            tree.append(node)
        else:
            stack[-1]['node']['children'].append(node)
            
        stack.append({'level': level, 'node': node})
    
    # Process tree to add 'self' data columns for parents
    def process_parents(nodes):
        import copy
        for node in nodes:
            if node['children']:
                # Add a synthetic child for the parent's own data
                self_node = copy.deepcopy(node)
                self_node['children'] = []
                # Remove the original label to avoid confusing it with the parent title
                self_node['field']['label'] = "Всего"
                # Принудительно ставим тип number, чтобы колонка 'Всего' могла суммироваться в строке Итого
                self_node['field']['type'] = 'number'
                
                # Prepend the synthetic node to children
                node['children'].insert(0, self_node)
                process_parents(node['children'][1:]) # skip the synthetic one we just added
    
    process_parents(tree)
    
    # Calculate depth and spans
    def get_max_depth(nodes):
        if not nodes: return 0
        max_d = 0
        for n in nodes:
            if n['children']:
                max_d = max(max_d, 1 + get_max_depth(n['children']))
            else:
                max_d = max(max_d, 1)
        return max_d
        
    def get_colspan(node):
        if not node['children']: return 1
        return sum(get_colspan(c) for c in node['children'])

    max_depth = get_max_depth(tree)
    if max_depth == 0: max_depth = 1
    
    header_rows = [[] for _ in range(max_depth)]
    leaf_fields = []
    
    def build_headers(nodes, current_depth):
        for node in nodes:
            colspan = get_colspan(node)
            label = node['field'].get('label', '')
            hint = node['field'].get('hint', '')
            
            if not node['children']:
                header_rows[current_depth].append({
                    'label': label,
                    'hint': hint,
                    'colspan': 1, 
                    'rowspan': max_depth - current_depth
                })
                leaf_fields.append(node['field'])
            else:
                header_rows[current_depth].append({
                    'label': label,
                    'hint': hint,
                    'colspan': colspan, 
                    'rowspan': 1
                })
                build_headers(node['children'], current_depth + 1)
                
    build_headers(tree, 0)
    
    return header_rows, leaf_fields

