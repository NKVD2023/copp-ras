import time

class ExcelParser:
    @staticmethod
    def parse_workbook(wb):
        schema = []
        
        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            ws = wb[sheet_name]
            
            # ШАГ 1: Находим реальное количество колонок (max_col), игнорируя полностью пустые крайние столбцы
            actual_max_col = 0
            for r in range(1, min((ws.max_row or 1) + 1, 30)):
                for c in range(1, (ws.max_column or 1) + 1):
                    if ws.cell(row=r, column=c).value is not None:
                        actual_max_col = max(actual_max_col, c)
                        
            if actual_max_col < 1:
                continue
                
            # ЭВРИСТИКА: Пытаемся автоматически определить, где заканчивается шапка таблицы.
            header_max_row = min((ws.max_row or 1), 30)
            for r in range(1, header_max_row + 1):
                vals = [str(ws.cell(row=r, column=c).value).strip() for c in range(1, actual_max_col + 1) if ws.cell(row=r, column=c).value is not None]
                if not vals: continue
                
                # Ищем строку с нумерацией (типа 1, 2, 3...) - это явный признак конца шапки
                if len(vals) >= 3 and vals[0] == '1' and vals[1] == '2' and vals[2] == '3':
                    header_max_row = r
                    break
                # Или если строка содержит короткие цифры (альтернативная нумерация)
                if len(vals) >= 2 and vals[0] == '1' and vals[1] == '2':
                    short_count = sum(1 for v in vals if len(v) <= 5)
                    if short_count / len(vals) > 0.5:
                        header_max_row = r
                        break
                
            def get_merge_info(r, c):
                """Вспомогательная функция для корректного чтения объединенных (Merged) ячеек"""
                for merge_range in ws.merged_cells.ranges:
                    if merge_range.min_row <= r <= merge_range.max_row and \
                       merge_range.min_col <= c <= merge_range.max_col:
                        return {
                            'val': ws.cell(row=merge_range.min_row, column=merge_range.min_col).value,
                            'width': merge_range.max_col - merge_range.min_col + 1
                        }
                return {'val': ws.cell(row=r, column=c).value, 'width': 1}

            # ШАГ 2: Собираем пути заголовков для каждой колонки
            paths = []
            for col_idx in range(1, actual_max_col + 1):
                path = []
                empty_count = 0
                
                for row_idx in range(1, header_max_row + 1):
                    info = get_merge_info(row_idx, col_idx)
                    val = info['val']
                    width = info['width']
                    
                    v_str = str(val).strip().replace('\n', ' ') if val is not None else ""
                    
                    if v_str:
                        empty_count = 0
                        # Пропускаем глобальные "над-заголовки" (которые растянуты на бОльшую часть таблицы)
                        if width > actual_max_col * 0.75 and width > 2:
                            continue
                        
                        # Избегаем дублирования текста при вертикальном объединении ячеек
                        if v_str not in path:
                            path.append(v_str)
                    else:
                        empty_count += 1
                        
                    # Если 3 пустые ячейки подряд — считаем, что шапка над этим столбцом закончилась
                    if empty_count >= 3:
                        break
                
                full_label = " - ".join(path).lower()
                # Игнорируем служебные колонки
                if 'организация' in full_label and len(full_label) < 30:
                    continue
                if full_label in ['№', '№ п/п', 'n', 'п/п', '№ п\\п', 'номер']:
                    continue
                    
                if path:
                    paths.append(path)

            # ШАГ 3: Строим дерево из путей
            class Node:
                def __init__(self, label):
                    self.label = label
                    self.children = []
                def get_child(self, lbl):
                    for c in self.children:
                        if c.label == lbl: return c
                    return None

            root = Node("root")
            for path in paths:
                current = root
                for p in path:
                    child = current.get_child(p)
                    if not child:
                        child = Node(p)
                        current.children.append(child)
                    current = child

            # ШАГ 4: Разворачиваем дерево обратно в плоский массив с isGroup и level (DFS)
            fields = []
            def dfs(node, level):
                if node.label != "root":
                    is_group = len(node.children) > 0
                    
                    type_val = 'Текстовое'
                    if not is_group:
                        lower_label = node.label.lower()
                        numeric_keywords = ['количество', 'кол-во', 'сколько', 'число', 'сумма', 'всего', 'из них']
                        if any(kw in lower_label for kw in numeric_keywords):
                            type_val = 'Числовое'
                            
                    # Генерируем уникальный внутренний ID поля
                    timestamp = str(int(time.time() * 1000) + len(fields))[-6:]
                    field_id = f"s{sheet_idx}_c{len(fields)}_{timestamp}"
                    
                    fields.append({
                        'id': field_id,       # Новый формат
                        'name': field_id,     # Для обратной совместимости
                        'label': node.label,
                        'type': type_val,
                        'required': False,
                        'isGroup': is_group,
                        'level': max(0, level)
                    })
                
                for c in node.children:
                    dfs(c, level + 1 if node.label != "root" else 0)

            dfs(root, -1)
            
            # Добавляем лист в структуру отчета только если на нем есть распознанные колонки
            if fields:
                schema.append({
                    'sheet_title': sheet_name,
                    'fields': fields
                })
                
        return schema
