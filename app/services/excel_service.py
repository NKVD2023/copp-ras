import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import re

class ExcelService:
    @staticmethod
    def export_debtors(template, debtors):
        """
        Формирует Excel файл со списком должников.
        :param template: Объект ReportTemplate
        :param debtors: Список объектов User (должники)
        :return: (output: BytesIO, filename: str)
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Должники"
        
        # Настройка заголовка
        ws.append(["Организация"])
        header_cell = ws.cell(row=1, column=1)
        header_cell.font = Font(bold=True, color="FFFFFF")
        header_cell.fill = PatternFill(start_color="00334E", end_color="00334E", fill_type="solid")
        header_cell.alignment = Alignment(horizontal="center", vertical="center")
        
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        header_cell.border = thin_border
        
        # Ширина колонки
        ws.column_dimensions['A'].width = 80
        
        # Заполнение данных
        for row_idx, d in enumerate(debtors, start=2):
            org_name = d.description if d.description else d.username
            cell = ws.cell(row=row_idx, column=1, value=org_name)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Должники_{template.short_name}.xlsx".replace(" ", "_")
        return output, filename

    @staticmethod
    def export_statistics(stat_schema, short_name, user_title=None):
        """
        Формирует Excel файл со сводной статистикой.
        Макет: периоды вертикально (от новых к старым), поля горизонтально.
        :param stat_schema: Словарь с периодами и полями (с дельтами).
        :param short_name: Тип отчета.
        :param user_title: Имя учреждения (для админа) или None (для пользователя).
        :return: (output: BytesIO, filename: str)
        """
        CORP_COLOR  = "00334E"
        COLOR_UP    = "16A34A"
        COLOR_DOWN  = "DC2626"
        COLOR_EMPTY = "94A3B8"

        header_font = Font(bold=True, color="FFFFFF", name='Arial', size=11)
        header_fill = PatternFill(start_color=CORP_COLOR, end_color=CORP_COLOR, fill_type="solid")
        period_font = Font(bold=True, color="1E293B", name='Arial', size=11)
        period_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        data_font   = Font(name='Arial', size=11)
        thin_border = Border(
            left=Side(style='thin',   color='BFBFBF'),
            right=Side(style='thin',  color='BFBFBF'),
            top=Side(style='thin',    color='BFBFBF'),
            bottom=Side(style='thin', color='BFBFBF')
        )
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Статистика"

        periods = stat_schema.get("periods", [])
        fields  = stat_schema.get("fields",  [])

        period_order = list(reversed(range(len(periods))))
        total_cols = 1 + len(fields)

        # ---- Строка 1: заголовок ----
        title_text = f"Статистика: {short_name}"
        if user_title:
            title_text += f" | {user_title}"

        title_cell = ws.cell(row=1, column=1, value=title_text)
        title_cell.font      = Font(bold=True, size=14, color="FFFFFF", name='Arial')
        title_cell.fill      = header_fill
        title_cell.alignment = align_center
        title_cell.border    = thin_border
        if total_cols > 1:
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
            for col in range(2, total_cols + 1):
                c = ws.cell(row=1, column=col)
                c.fill   = header_fill
                c.border = thin_border
        ws.row_dimensions[1].height = 36

        # ---- Строка 2: шапка (Период | Поле_1 | Поле_2 | ...) ----
        ws.cell(row=2, column=1, value="Период")
        for j, field in enumerate(fields):
            ws.cell(row=2, column=2 + j, value=field["name"])

        for col in range(1, total_cols + 1):
            cell = ws.cell(row=2, column=col)
            cell.font      = header_font
            cell.fill      = header_fill
            cell.alignment = align_center
            cell.border    = thin_border

        # ---- Строки 3+: периоды (от новых к старым) ----
        current_row = 3
        for p_idx in period_order:
            period_info = periods[p_idx]
            period_label = period_info["period"]
            if period_info.get("end_date"):
                period_label += f"\nпо {period_info['end_date']}"

            # 1. Вычисляем max_len
            max_len = 1
            has_submission = False
            for field in fields:
                val_data = field["values"][p_idx]
                if val_data["has_data"]:
                    has_submission = True
                    val = val_data["value"]
                    if isinstance(val, list):
                        max_len = max(max_len, len(val))

            start_merge_row = current_row

            # 2. Генерируем строки
            for i in range(max_len):
                if i == 0:
                    period_cell           = ws.cell(row=current_row, column=1, value=period_label)
                    period_cell.font      = period_font
                    period_cell.fill      = period_fill
                    period_cell.alignment = align_center
                    period_cell.border    = thin_border
                else:
                    # Пустая ячейка, будет объединена
                    period_cell           = ws.cell(row=current_row, column=1)
                    period_cell.border    = thin_border

                for j, field in enumerate(fields):
                    val_data = field["values"][p_idx]
                    cell     = ws.cell(row=current_row, column=2 + j)

                    if val_data["has_data"]:
                        val = val_data["value"]
                        cell_val = "-"
                        if isinstance(val, list):
                            if i < len(val):
                                cell_val = val[i]
                        else:
                            if i == 0:
                                cell_val = val
                            else:
                                cell_val = "" # Будет объединена
                        
                        if cell_val not in ["", None, "-"]:
                            if val_data.get("type") in ["number", "float"] or (isinstance(cell_val, (int, float, str)) and str(cell_val).replace('.', '', 1).replace(',', '', 1).replace('-', '', 1).isdigit()):
                                try:
                                    cell_val = float(str(cell_val).replace(',', '.')) if "." in str(cell_val) or "," in str(cell_val) else int(cell_val)
                                except (ValueError, TypeError):
                                    pass

                        cell.value = cell_val if cell_val != "" else None
                        
                        if i == 0:
                            status = val_data.get("status", "zero")
                            if status == "up":
                                cell.font = Font(color=COLOR_UP,   bold=True, name='Arial', size=11)
                            elif status == "down":
                                cell.font = Font(color=COLOR_DOWN, bold=True, name='Arial', size=11)
                            else:
                                cell.font = data_font
                        else:
                            cell.font = data_font
                    else:
                        if i == 0:
                            cell.value = "Нет данных"
                            cell.font  = Font(color=COLOR_EMPTY, italic=True, name='Arial', size=11)
                        else:
                            cell.value = None

                    cell.alignment = align_center
                    cell.border    = thin_border
                
                current_row += 1
            
            # 3. Объединение ячеек для периода и скалярных полей
            if max_len > 1:
                ws.merge_cells(start_row=start_merge_row, start_column=1, end_row=current_row-1, end_column=1)
                for j, field in enumerate(fields):
                    val_data = field["values"][p_idx]
                    if val_data["has_data"]:
                        val = val_data["value"]
                        if not isinstance(val, list):
                            ws.merge_cells(start_row=start_merge_row, start_column=2+j, end_row=current_row-1, end_column=2+j)
                    else:
                        ws.merge_cells(start_row=start_merge_row, start_column=2+j, end_row=current_row-1, end_column=2+j)
                
                # 4. Строка "Итого"
                total_fill_style = PatternFill("solid", fgColor="F8F9FA")
                total_font_style = Font(name='Arial', size=11, bold=True)
                
                ws.cell(row=current_row, column=1, value="Итого").font = total_font_style
                ws.cell(row=current_row, column=1).fill = total_fill_style
                ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="left", vertical="center")
                ws.cell(row=current_row, column=1).border = thin_border
                
                for j, field in enumerate(fields):
                    val_data = field["values"][p_idx]
                    cell = ws.cell(row=current_row, column=2 + j)
                    cell.fill = total_fill_style
                    cell.font = total_font_style
                    cell.alignment = align_center
                    cell.border = thin_border
                    
                    if val_data["has_data"] and val_data.get("type") in ["number", "float"]:
                        val = val_data["value"]
                        total = 0.0
                        has_total = False
                        if isinstance(val, list):
                            for v in val:
                                if v is not None and str(v).strip() != "":
                                    try:
                                        v_clean = str(v).replace(',', '.')
                                        total += float(v_clean)
                                        has_total = True
                                    except ValueError:
                                        pass
                        elif val is not None and str(val).strip() != "":
                            try:
                                v_clean = str(val).replace(',', '.')
                                total += float(v_clean)
                                has_total = True
                            except ValueError:
                                pass
                        
                        if has_total:
                            cell.value = total if total % 1 != 0 else int(total)
                        else:
                            cell.value = 0
                    else:
                        cell.value = "-"
                
                current_row += 1

        # Авто-размер ячеек
        ExcelService._autosize_excel(ws)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        safe_name = short_name.replace(" ", "_").replace("/", "-")
        filename = f"Статистика_{safe_name}.xlsx"
        return output, filename

    @staticmethod
    def export_report(template, submissions):
        """
        Формирует сводный Excel файл со сданными отчетами (поддержка сложной шапки).
        :param template: Объект ReportTemplate
        :param submissions: Список объектов ReportSubmission
        :return: (output: BytesIO, filename: str)
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        # --- НАСТРОЙКИ СТИЛЕЙ ---
        title_font = Font(name='Arial', size=14, bold=True, color="000000")
        header_font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="00334E")
        data_font = Font(name='Arial', size=11)
        total_font = Font(name='Arial', size=11, bold=True)
        total_fill = PatternFill("solid", fgColor="F8F9FA")
        
        thin_border = Border(
            left=Side(style='thin', color='BFBFBF'),
            right=Side(style='thin', color='BFBFBF'),
            top=Side(style='thin', color='BFBFBF'),
            bottom=Side(style='thin', color='BFBFBF')
        )
        
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

        for sheet_data in template.schema:
            safe_title = re.sub(r'[\\*?:/\[\]]', '', sheet_data['sheet_title'])[:31]
            ws = wb.create_sheet(title=safe_title)

            fields = sheet_data.get('fields', [])
            
            from app.utils import build_table_headers
            header_rows, leaf_fields = build_table_headers(fields)
            max_depth = len(header_rows) if header_rows else 1
            
            # Общее количество колонок = 1 (Организация) + количество полей данных
            max_col = len(leaf_fields) + 1

            # 1. ЗАГОЛОВОК ЛИСТА
            title_cell = ws.cell(row=1, column=1, value=template.name)
            title_cell.font = title_font
            title_cell.alignment = align_center
            
            for col in range(1, max_col + 1):
                ws.cell(row=1, column=col).border = thin_border
                
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
            ws.row_dimensions[1].height = 60

            # 2. РЕНДЕР СЛОЖНОЙ ШАПКИ
            start_row = 2
            
            # Устанавливаем стили для всей области шапки заранее
            for r in range(start_row, start_row + max_depth):
                ws.row_dimensions[r].height = 40
                for c in range(1, max_col + 1):
                    cell = ws.cell(row=r, column=c)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = align_center
                    cell.border = thin_border

            # Заголовок первой колонки
            ws.cell(row=start_row, column=1, value="Организация")
            if max_depth > 1:
                ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row + max_depth - 1, end_column=1)

            # Отрисовываем древовидную шапку
            occupied = set()
            for row_idx, h_row in enumerate(header_rows):
                c_row = start_row + row_idx
                current_col = 2 # Начинаем со 2 колонки
                for cell_info in h_row:
                    # Пропускаем колонки, которые уже заняты через rowspan сверху
                    while (c_row, current_col) in occupied:
                        current_col += 1
                        
                    ws.cell(row=c_row, column=current_col, value=cell_info['label'])
                    
                    # Помечаем все ячейки, которые занимает этот заголовок, как занятые
                    for r in range(c_row, c_row + cell_info['rowspan']):
                        for c in range(current_col, current_col + cell_info['colspan']):
                            occupied.add((r, c))
                    
                    if cell_info['colspan'] > 1 or cell_info['rowspan'] > 1:
                        ws.merge_cells(
                            start_row=c_row, 
                            start_column=current_col, 
                            end_row=c_row + cell_info['rowspan'] - 1, 
                            end_column=current_col + cell_info['colspan'] - 1
                        )

            # Ширина колонок
            ws.column_dimensions['A'].width = 50 
            for col_idx in range(2, max_col + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 25

            # 3. ДАННЫЕ
            current_row = start_row + max_depth
            
            for sub in submissions:
                org_name = sub.user.description if sub.user.description else sub.user.username
                
                # 1. Determine if has_data and calculate max_len
                has_data = False
                max_len = 1
                for f in leaf_fields:
                    field_key = f.get('name') or f.get('id')
                    val = sub.data.get(field_key)
                    if val is not None:
                        if isinstance(val, list):
                            for v in val:
                                if v is not None and str(v).strip() != "":
                                    has_data = True
                            max_len = max(max_len, len(val))
                        elif str(val).strip() != "":
                            has_data = True
                
                if not has_data:
                    continue
                
                start_merge_row = current_row
                sub_totals = {f.get('name') or f.get('id'): 0.0 for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}
                has_subtotals = {f.get('name') or f.get('id'): False for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}

                # 2. Generate max_len rows
                for i in range(max_len):
                    row_data = [org_name if i == 0 else ""]
                    
                    for f in leaf_fields:
                        field_key = f.get('name') or f.get('id')
                        val = sub.data.get(field_key)
                        
                        f_type = str(f.get('type', '')).lower()
                        is_numeric = f_type in ['number', 'числовое']
                        
                        cell_val = "-"
                        if isinstance(val, list):
                            if i < len(val):
                                cell_val = val[i]
                        else:
                            if i == 0:
                                cell_val = val
                            else:
                                cell_val = ""
                                
                        if cell_val in [None, '', []]:
                            cell_val = "-"
                            
                        if is_numeric and cell_val != "-":
                            try:
                                cell_num = float(cell_val)
                                cell_val = cell_num
                                sub_totals[field_key] += cell_num
                                has_subtotals[field_key] = True
                            except (ValueError, TypeError):
                                pass
                                
                        row_data.append(cell_val)

                    ws.append(row_data)
                    
                    for col_idx, _ in enumerate(row_data, 1):
                        cell = ws.cell(row=current_row, column=col_idx)
                        cell.font = data_font
                        cell.border = thin_border
                        cell.alignment = align_left if col_idx == 1 else align_center
                    
                    current_row += 1
                
                # 3. Merge vertical cells for scalars and org name
                if max_len > 1:
                    ws.merge_cells(start_row=start_merge_row, start_column=1, end_row=start_merge_row + max_len - 1, end_column=1)
                    
                    col_idx = 2
                    for f in leaf_fields:
                        field_key = f.get('name') or f.get('id')
                        val = sub.data.get(field_key)
                        if not isinstance(val, list):
                            ws.merge_cells(start_row=start_merge_row, start_column=col_idx, end_row=start_merge_row + max_len - 1, end_column=col_idx)
                        col_idx += 1
                        
                    # 4. Add subtotal row
                    subtotal_row = ['Итого по организации']
                    for f in leaf_fields:
                        field_key = f.get('name') or f.get('id')
                        f_type = str(f.get('type', '')).lower()
                        if f_type in ['number', 'числовое']:
                            if has_subtotals[field_key]:
                                subtotal_row.append(sub_totals[field_key])
                            else:
                                subtotal_row.append(0)
                        else:
                            subtotal_row.append('-')
                            
                    ws.append(subtotal_row)
                    
                    subtotal_font = Font(name='Arial', size=10, bold=True)
                    for col_idx, _ in enumerate(subtotal_row, 1):
                        cell = ws.cell(row=current_row, column=col_idx)
                        cell.font = subtotal_font
                        cell.border = thin_border
                        cell.alignment = align_left if col_idx == 1 else align_center
                        # Highlight row with light gray background
                        cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
                            
                    current_row += 1

            # 4. ИТОГО
            total_row = ['Итого']
            for f in leaf_fields:
                f_type = str(f.get('type', '')).lower()
                if f_type in ['number', 'числовое']:
                    col_total = 0
                    has_data = False
                    for sub in submissions:
                        field_key = f.get('name') or f.get('id')
                        val = sub.data.get(field_key)
                        if val:
                            if isinstance(val, list):
                                for v in val:
                                    if v:
                                        try:
                                            col_total += float(v)
                                            has_data = True
                                        except (ValueError, TypeError):
                                            pass
                            else:
                                try:
                                    col_total += float(val)
                                    has_data = True
                                except (ValueError, TypeError):
                                    pass
                    total_row.append(col_total if has_data else 0)
                else:
                    total_row.append('-')

            ws.append(total_row)
            
            # Применяем авто-размер ячеек к текущему листу
            ExcelService._autosize_excel(ws)

            for col_idx in range(1, max_col + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.font = total_font
                cell.fill = total_fill
                cell.border = thin_border
                cell.alignment = align_left if col_idx == 1 else align_center

        filename = f"Свод_{template.short_name}.xlsx".replace(" ", "_")
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output, filename

    @staticmethod
    def _autosize_excel(ws, min_col_width=12, max_col_width=60, default_row_height=15):
        from openpyxl.utils import get_column_letter
        
        # Авто-размер колонок
        for col in ws.columns:
            max_length = 0
            col_letter = None
            for cell in col:
                if col_letter is None:
                    col_letter = get_column_letter(cell.column)
                if cell.value:
                    try:
                        lines = str(cell.value).split("\n")
                        for line in lines:
                            if len(line) > max_length:
                                max_length = len(line)
                    except:
                        pass
            
            if col_letter:
                adjusted_width = min(max(max_length + 2, min_col_width), max_col_width)
                ws.column_dimensions[col_letter].width = adjusted_width
                
        # Авто-высота строк
        for row in ws.rows:
            if not row:
                continue
            max_lines = 1
            for cell in row:
                if cell.value:
                    try:
                        col_letter = get_column_letter(cell.column)
                        col_width = ws.column_dimensions[col_letter].width
                        if not col_width:
                            col_width = min_col_width
                        lines = str(cell.value).split("\n")
                        total_lines_for_cell = sum(max(1, -(-len(line) // int(col_width))) for line in lines)
                        if total_lines_for_cell > max_lines:
                            max_lines = total_lines_for_cell
                    except:
                        pass
            ws.row_dimensions[row[0].row].height = max_lines * default_row_height + 5
