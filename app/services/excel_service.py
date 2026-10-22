import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import re
import json
from datetime import datetime

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
        
        safe_name = re.sub(r'[^\w\s-]', '', template.short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"Должники_{safe_name}.xlsx"
        return output, filename

    @staticmethod
    def export_revisions(template, revisions):
        """
        Формирует Excel файл со списком учреждений на доработке и замечаниями куратора.
        :param template: Объект ReportTemplate
        :param revisions: Список объектов ReportSubmission (со статусом is_revision=True)
        :return: (output: BytesIO, filename: str)
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "На доработке"
        
        headers = ["Организация", "Дата возврата", "Замечание куратора / Причина возврата"]
        ws.append(headers)
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="FF0072", end_color="FF0072", fill_type="solid")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col_idx in range(1, 4):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
            
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 70
        ws.row_dimensions[1].height = 28
        
        for row_idx, r in enumerate(revisions, start=2):
            org_name = (r.user.description if r.user and r.user.description else (r.user.username if r.user else "—"))
            date_str = r.returned_at.strftime('%d.%m.%Y %H:%M') if r.returned_at else "—"
            comment = r.revision_comment or "Без замечания"
            
            c1 = ws.cell(row=row_idx, column=1, value=org_name)
            c2 = ws.cell(row=row_idx, column=2, value=date_str)
            c3 = ws.cell(row=row_idx, column=3, value=comment)
            
            c1.border = thin_border
            c1.alignment = Alignment(vertical="center", wrap_text=True)
            
            c2.border = thin_border
            c2.alignment = Alignment(horizontal="center", vertical="center")
            
            c3.border = thin_border
            c3.alignment = Alignment(vertical="center", wrap_text=True)
            
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        safe_name = re.sub(r'[^\w\s-]', '', template.short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"На_доработке_{safe_name}.xlsx"
        return output, filename

    @staticmethod
    def export_statistics(stat_schema, short_name, user_title=None):
        """
        Формирует Excel файл со сводной статистикой.
        Макет: периоды вертикально (от новых к старым), поля горизонтально.
        :param stat_schema: Список листов (как в веб-дашборде)
        :param short_name: Тип отчета.
        :param user_title: Имя учреждения (для админа) или None (для пользователя).
        :return: (output: BytesIO, filename: str)
        """
        CORP_COLOR  = "00334E"
        COLOR_UP    = "16A34A"
        COLOR_DOWN  = "DC2626"
        COLOR_EMPTY = "94A3B8"

        title_font = Font(bold=True, size=16, color="000000", name='Arial')
        header_font = Font(bold=True, color="FFFFFF", name='Arial', size=11)
        header_fill = PatternFill(start_color=CORP_COLOR, end_color=CORP_COLOR, fill_type="solid")
        period_font = Font(bold=True, color="1E293B", name='Arial', size=11)
        period_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        data_font   = Font(name='Arial', size=11)
        
        thin_border = Border(
            left=Side(style='thin', color='BFBFBF'),
            right=Side(style='thin', color='BFBFBF'),
            top=Side(style='thin', color='BFBFBF'),
            bottom=Side(style='thin', color='BFBFBF')
        )
        
        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # Удаляем дефолтный лист

        for sheet_index, sheet_data in enumerate(stat_schema):
            title = sheet_data.get('sheet_title', f'Лист {sheet_index+1}')
            safe_title = re.sub(r'[\\*?:/\[\]]', '', title)[:31]
            ws = wb.create_sheet(title=safe_title)

            header_rows = sheet_data.get('header_rows', [])
            leaf_fields = sheet_data.get('leaf_fields', [])
            periods_data = sheet_data.get('periods_data', [])
            
            max_depth = len(header_rows) if header_rows else 1
            max_col = len(leaf_fields) + 1

            # 1. ЗАГОЛОВОК ЛИСТА
            title_text = f"Статистика: {short_name}"
            if user_title:
                title_text += f" | {user_title}"
            
            title_cell = ws.cell(row=1, column=1, value=title_text)
            title_cell.font = title_font
            title_cell.alignment = align_center
            
            for col in range(1, max_col + 1):
                ws.cell(row=1, column=col).border = thin_border
                
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
            ws.row_dimensions[1].height = 60

            # 2. РЕНДЕР СЛОЖНОЙ ШАПКИ
            start_row = 2
            
            for r in range(start_row, start_row + max_depth):
                ws.row_dimensions[r].height = 40
                for c in range(1, max_col + 1):
                    cell = ws.cell(row=r, column=c)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = align_center
                    cell.border = thin_border

            ws.cell(row=start_row, column=1, value="Период")
            if max_depth > 1:
                ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row + max_depth - 1, end_column=1)

            occupied = set()
            for row_idx, h_row in enumerate(header_rows):
                c_row = start_row + row_idx
                current_col = 2
                for cell_info in h_row:
                    while (c_row, current_col) in occupied:
                        current_col += 1
                        
                    ws.cell(row=c_row, column=current_col, value=cell_info['label'])
                    
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

            # 3. ДАННЫЕ
            current_row = start_row + max_depth
            
            for p_data in periods_data:
                period_label = p_data["period"]
                
                max_len = 1
                if p_data["has_submission"]:
                    for f in leaf_fields:
                        f_id = str(f.get('name') or f.get('id', ''))
                        val = p_data['values'].get(f_id)
                        if isinstance(val, list):
                            max_len = max(max_len, len(val))

                start_merge_row = current_row

                for i in range(max_len):
                    if i == 0:
                        period_cell = ws.cell(row=current_row, column=1, value=period_label)
                        period_cell.font = period_font
                        period_cell.fill = period_fill
                        period_cell.alignment = align_center
                    else:
                        period_cell = ws.cell(row=current_row, column=1)
                        
                    period_cell.border = thin_border

                    for j, f in enumerate(leaf_fields):
                        f_id = str(f.get('name') or f.get('id', ''))
                        cell = ws.cell(row=current_row, column=2 + j)
                        
                        cell_val = "-"
                        if p_data["has_submission"]:
                            val = p_data['values'].get(f_id)
                            if isinstance(val, list):
                                if i < len(val):
                                    cell_val = val[i]
                            else:
                                if i == 0:
                                    cell_val = val
                                else:
                                    cell_val = ""
                        else:
                            if i == 0:
                                cell_val = "Нет данных"
                            else:
                                cell_val = ""

                        if cell_val in [None, '', []]:
                            cell_val = "-"

                        is_numeric = str(f.get('type', '')).lower() in ['number', 'числовое']
                        if is_numeric and cell_val not in ["-", "Нет данных", ""]:
                            try:
                                cell_num = float(str(cell_val).replace(',', '.')) if "." in str(cell_val) or "," in str(cell_val) else int(cell_val)
                                cell_val = cell_num
                            except (ValueError, TypeError):
                                pass
                                
                        cell.value = cell_val if cell_val != "" else None
                        
                        if i == 0 and is_numeric and "deltas" in p_data and f_id in p_data["deltas"]:
                            delta = p_data["deltas"][f_id]
                            if delta > 0:
                                cell.font = Font(color=COLOR_UP, bold=True, name='Arial', size=11)
                            elif delta < 0:
                                cell.font = Font(color=COLOR_DOWN, bold=True, name='Arial', size=11)
                            else:
                                cell.font = data_font
                        elif cell_val == "Нет данных":
                            cell.font = Font(color=COLOR_EMPTY, italic=True, name='Arial', size=11)
                        else:
                            cell.font = data_font
                            
                        cell.alignment = align_center
                        cell.border = thin_border
                        
                    current_row += 1

                if max_len > 1:
                    ws.merge_cells(start_row=start_merge_row, start_column=1, end_row=current_row-1, end_column=1)
                    
                    for j, f in enumerate(leaf_fields):
                        f_id = str(f.get('name') or f.get('id', ''))
                        val = p_data['values'].get(f_id) if p_data["has_submission"] else None
                        if not isinstance(val, list):
                            ws.merge_cells(start_row=start_merge_row, start_column=2+j, end_row=current_row-1, end_column=2+j)
                current_row += 1

            ws.column_dimensions['A'].width = 35
            for col_idx in range(2, max_col + 1):
                from openpyxl.utils import get_column_letter
                ws.column_dimensions[get_column_letter(col_idx)].width = 20

            # Авто-размер ячеек
            ExcelService._autosize_excel(ws)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        safe_name = re.sub(r'[^\w\s-]', '', short_name).strip().replace(" ", "_")
        if len(safe_name) > 50: safe_name = safe_name[:50] + "..."
        filename = f"Статистика_{safe_name}.xlsx"
        return output, filename

    @staticmethod
    def _sanitize_sheet_title(base_name, used_titles):
        """
        Очищает имя листа от недопустимых символов Excel (\, /, ?, *, :, [, ]),
        ограничивает длину до 31 символа и предотвращает коллизии имен (case-insensitive).
        """
        clean_name = re.sub(r'[\\*?:/\[\]]', '', str(base_name or '')).strip()
        if not clean_name:
            clean_name = "Лист"
        clean_name = clean_name[:31]

        candidate = clean_name
        counter = 1
        while candidate.lower() in used_titles:
            suffix = f"_{counter}"
            candidate = clean_name[:31 - len(suffix)] + suffix
            counter += 1

        used_titles.add(candidate.lower())
        return candidate

    @staticmethod
    def _render_sheet_content(ws, sheet_data, submissions, report_title):
        """
        Рендерит сводные данные одного листа отчета в переданный worksheet openpyxl.
        """
        from app.utils import build_table_headers

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

        fields = sheet_data.get('fields', [])
        header_rows, leaf_fields = build_table_headers(fields)
        max_depth = len(header_rows) if header_rows else 1
        max_col = len(leaf_fields) + 2

        # 1. ЗАГОЛОВОК ЛИСТА
        title_cell = ws.cell(row=1, column=1, value=report_title)
        title_cell.font = title_font
        title_cell.alignment = align_center

        for col in range(1, max_col + 1):
            ws.cell(row=1, column=col).border = thin_border

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        ws.row_dimensions[1].height = 60

        # 2. РЕНДЕР СЛОЖНОЙ ШАПКИ
        start_row = 2
        for r in range(start_row, start_row + max_depth):
            ws.row_dimensions[r].height = 40
            for c in range(1, max_col + 1):
                cell = ws.cell(row=r, column=c)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = align_center
                cell.border = thin_border

        ws.cell(row=start_row, column=1, value="Организация")
        ws.cell(row=start_row, column=2, value="ID")
        if max_depth > 1:
            ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row + max_depth - 1, end_column=1)
            ws.merge_cells(start_row=start_row, start_column=2, end_row=start_row + max_depth - 1, end_column=2)

        occupied = set()
        for row_idx, h_row in enumerate(header_rows):
            c_row = start_row + row_idx
            current_col = 3
            for cell_info in h_row:
                while (c_row, current_col) in occupied:
                    current_col += 1

                ws.cell(row=c_row, column=current_col, value=cell_info['label'])

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
                    if cell_info['colspan'] >= 3:
                        ws.cell(row=c_row, column=current_col).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)

        # Скрытые подсказки с системным именем поля в шапке (для гарантированного обратного импорта)
        from openpyxl.comments import Comment
        from openpyxl.cell.cell import MergedCell
        bottom_header_row = start_row + max_depth - 1
        for idx, f in enumerate(leaf_fields):
            f_col = 3 + idx
            f_key = f.get('name') or f.get('id')
            if f_key:
                try:
                    # Устанавливаем комментарий во все доступные (не объединенные) ячейки шапки данной колонки
                    for r_chk in range(start_row, bottom_header_row + 1):
                        cell_to_comment = ws.cell(row=r_chk, column=f_col)
                        if not isinstance(cell_to_comment, MergedCell):
                            cell_to_comment.comment = Comment(f"field_key:{f_key}", "COPP")
                except Exception:
                    pass

        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['B'].hidden = True
        for col_idx in range(3, max_col + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 25

        # 3. ДАННЫЕ
        current_row = start_row + max_depth

        # Фильтруем организации, доступные для данного листа
        t_groups = sheet_data.get('target_groups', [])
        old_group = sheet_data.get('target_group')
        all_t_groups = list(t_groups) + ([old_group] if old_group and old_group not in t_groups else [])

        sheet_subs = []
        for s in submissions:
            user = getattr(s, 'user', None)
            is_manual = getattr(s, 'is_manual', False)
            if not user and not is_manual:
                continue
            if user and not is_manual and all_t_groups and getattr(user, 'group', None) and user.group not in all_t_groups:
                continue
            sheet_subs.append(s)

        from app.reports.routes_data import get_sort_key
        sheet_subs.sort(key=get_sort_key)

        def render_sub_rows(sub, c_row):
            org_name = (sub.user.description if sub.user.description else sub.user.username) if getattr(sub, 'user', None) else getattr(sub, 'org_name', 'Организация')
            user_id = sub.user.id if (getattr(sub, 'user', None) and not getattr(sub, 'is_manual', False)) else ""

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
                return c_row, {}, {}

            start_merge_row = c_row
            sub_totals = {f.get('name') or f.get('id'): 0.0 for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}
            has_subtotals = {f.get('name') or f.get('id'): False for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}

            for i in range(max_len):
                row_data = [
                    org_name if i == 0 else "",
                    user_id if i == 0 else ""
                ]

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
                    cell = ws.cell(row=c_row, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx in [1, 2] else align_center

                c_row += 1

            if max_len > 1:
                ws.merge_cells(start_row=start_merge_row, start_column=1, end_row=start_merge_row + max_len - 1, end_column=1)
                ws.merge_cells(start_row=start_merge_row, start_column=2, end_row=start_merge_row + max_len - 1, end_column=2)

                col_idx = 3
                for f in leaf_fields:
                    field_key = f.get('name') or f.get('id')
                    val = sub.data.get(field_key)
                    if not isinstance(val, list):
                        ws.merge_cells(start_row=start_merge_row, start_column=col_idx, end_row=start_merge_row + max_len - 1, end_column=col_idx)
                    col_idx += 1

                subtotal_row = ['Итого по организации', '']
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
                    cell = ws.cell(row=c_row, column=col_idx)
                    cell.font = subtotal_font
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx in [1, 2] else align_center
                    cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

                c_row += 1

            return c_row, sub_totals, has_subtotals

        # Стилизация строки подгруппы
        subgroup_total_fill = PatternFill(start_color="EBF3FA", end_color="EBF3FA", fill_type="solid")
        subgroup_total_font = Font(name='Arial', size=11, bold=True, color="00334E")

        # Вывод учреждений строго по порядку в списке пользователей
        processed_subgroups = set()
        current_general_chunk = []

        for sub in sheet_subs:
            sg = (getattr(sub.user, 'subgroup', None) or '').strip() if sub.user else ''

            if not sg:
                current_general_chunk.append(sub)
            else:
                if sg in processed_subgroups:
                    continue

                # Выводим накопленные организации без подгруппы
                if current_general_chunk:
                    for g_sub in current_general_chunk:
                        current_row, _, _ = render_sub_rows(g_sub, current_row)
                    current_general_chunk = []

                # Собираем всех участников этой подгруппы в порядке списка пользователей
                sg_subs = [
                    s for s in sheet_subs
                    if (getattr(s.user, 'subgroup', None) or '').strip() == sg
                ]
                sg_subs.sort(key=get_sort_key)

                # Заголовочная строка подгруппы (обозначает начало группы в Excel)
                subgroup_header_row = [sg] + [''] * (max_col - 1)
                ws.append(subgroup_header_row)

                subgroup_header_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
                subgroup_header_font = Font(name='Arial', size=11, bold=True, color="00334E")

                for col_idx in range(1, max_col + 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = subgroup_header_font
                    cell.fill = subgroup_header_fill
                    cell.border = thin_border
                    cell.alignment = align_left

                if max_col > 1:
                    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=max_col)

                current_row += 1

                sg_accum_totals = {f.get('name') or f.get('id'): 0.0 for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}
                sg_has_totals = {f.get('name') or f.get('id'): False for f in leaf_fields if str(f.get('type', '')).lower() in ['number', 'числовое']}

                for s in sg_subs:
                    current_row, sub_totals, has_subtotals = render_sub_rows(s, current_row)
                    for k, v in sub_totals.items():
                        if has_subtotals.get(k):
                            sg_accum_totals[k] += v
                            sg_has_totals[k] = True

                # Строка промежуточного итога подгруппы: [Название подгруппы] всего (без кавычек)
                subgroup_total_row = [f"{sg} всего", '']
                for f in leaf_fields:
                    field_key = f.get('name') or f.get('id')
                    f_type = str(f.get('type', '')).lower()
                    if f_type in ['number', 'числовое']:
                        if sg_has_totals[field_key]:
                            val = sg_accum_totals[field_key]
                            subgroup_total_row.append(int(val) if val.is_integer() else round(val, 2))
                        else:
                            subgroup_total_row.append(0)
                    else:
                        subgroup_total_row.append('-')

                ws.append(subgroup_total_row)

                for col_idx, _ in enumerate(subgroup_total_row, 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = subgroup_total_font
                    cell.fill = subgroup_total_fill
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx in [1, 2] else align_center

                current_row += 1
                processed_subgroups.add(sg)

        # Выводим оставшиеся организации без подгруппы в конце
        if current_general_chunk:
            for g_sub in current_general_chunk:
                current_row, _, _ = render_sub_rows(g_sub, current_row)

        # 4. ИТОГО
        total_row = ['Итого', '']
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

        ExcelService._autosize_excel(ws)
        ws.column_dimensions['B'].hidden = True

        for col_idx in range(1, max_col + 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = thin_border
            cell.alignment = align_left if col_idx in [1, 2] else align_center

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

        used_titles = set()
        schema = template.schema if isinstance(template.schema, list) else json.loads(template.schema or '[]')
        for sheet_data in schema:
            safe_title = ExcelService._sanitize_sheet_title(sheet_data.get('sheet_title', 'Лист'), used_titles)
            ws = wb.create_sheet(title=safe_title)
            ExcelService._render_sheet_content(ws, sheet_data, submissions, template.name)

        safe_name = re.sub(r'[^\w\s-]', '', template.short_name).strip().replace(" ", "_")
        if len(safe_name) > 50:
            safe_name = safe_name[:50] + "..."
        filename = f"Свод_{safe_name}.xlsx"

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return output, filename

    @staticmethod
    def export_multi_reports(templates_data, include_toc=True):
        """
        Экспортирует несколько отчетов в единый файл Excel (.xlsx).
        Каждый отчет получает один или несколько листов (если в отчете несколько страниц схемы).
        При include_toc=True первым листом создается 'Оглавление' со ссылками на все листы.
        :param templates_data: список кортежей (template, submissions) или словарей {'template': t, 'submissions': s}
        :param include_toc: создавать ли лист 'Оглавление'
        :return: (output: BytesIO, filename: str)
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        TAB_COLORS = [
            '00334E', '0284C7', '16A34A', 'D97706',
            '9333EA', '2563EB', '0D9488', 'C026D3', 'EA580C', '4F46E5'
        ]

        items = []
        for item in templates_data:
            if isinstance(item, dict):
                items.append((item['template'], item.get('submissions', [])))
            else:
                items.append((item[0], item[1]))

        used_titles = set()
        if include_toc:
            used_titles.add("оглавление")

        report_summary = []

        for report_idx, (template, submissions) in enumerate(items):
            tab_color = TAB_COLORS[report_idx % len(TAB_COLORS)]
            schema = template.schema if isinstance(template.schema, list) else json.loads(template.schema or '[]')
            if not schema:
                schema = [{'sheet_title': 'Лист 1', 'fields': []}]

            sheet_count = len(schema)
            created_sheets = []

            for sheet_idx, sheet_data in enumerate(schema):
                if sheet_count == 1:
                    base_name = template.short_name or template.name or f"Отчет_{report_idx + 1}"
                else:
                    sheet_raw_title = sheet_data.get('sheet_title', f"Лист_{sheet_idx + 1}")
                    base_name = f"{template.short_name[:15]}_{sheet_raw_title[:13]}"

                sheet_title = ExcelService._sanitize_sheet_title(base_name, used_titles)
                ws = wb.create_sheet(title=sheet_title)
                ws.sheet_properties.tabColor = tab_color

                if sheet_count > 1:
                    sheet_header = f"{template.name} ({sheet_data.get('sheet_title', '')})"
                else:
                    sheet_header = template.name

                ExcelService._render_sheet_content(ws, sheet_data, submissions, sheet_header)
                created_sheets.append(sheet_title)

            report_summary.append({
                'template': template,
                'submissions_count': len(submissions),
                'sheets': created_sheets
            })

        # --- СОЗДАНИЕ ЛИСТА ОГЛАВЛЕНИЕ ---
        if include_toc and report_summary:
            ws_toc = wb.create_sheet(title="Оглавление", index=0)
            ws_toc.sheet_properties.tabColor = "00334E"

            title_font = Font(name='Arial', size=16, bold=True, color="00334E")
            subtitle_font = Font(name='Arial', size=10, italic=True, color="555555")
            th_font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
            th_fill = PatternFill("solid", fgColor="00334E")
            td_font = Font(name='Arial', size=11)
            link_font = Font(name='Arial', size=11, color="00334E", underline="single")
            zebra_fill = PatternFill("solid", fgColor="F8F9FA")

            thin_border = Border(
                left=Side(style='thin', color='D0D0D0'),
                right=Side(style='thin', color='D0D0D0'),
                top=Side(style='thin', color='D0D0D0'),
                bottom=Side(style='thin', color='D0D0D0')
            )

            ws_toc.cell(row=1, column=1, value="СВОДНЫЙ РЕЕСТР ОТЧЕТОВ").font = title_font
            ws_toc.row_dimensions[1].height = 32

            sub_val = f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Всего отчетов в пакете: {len(report_summary)}"
            ws_toc.cell(row=2, column=1, value=sub_val).font = subtitle_font
            ws_toc.row_dimensions[2].height = 20

            ws_toc.row_dimensions[3].height = 12

            headers = ["№", "Наименование отчета", "Период", "Сдано ответов", "Лист в книге (быстрый переход)"]
            start_row = 4
            ws_toc.row_dimensions[start_row].height = 28
            for col_idx, h_text in enumerate(headers, 1):
                c = ws_toc.cell(row=start_row, column=col_idx, value=h_text)
                c.font = th_font
                c.fill = th_fill
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                c.border = thin_border

            current_row = 5
            for rep_idx, rep_info in enumerate(report_summary, 1):
                t = rep_info['template']
                subs_cnt = rep_info['submissions_count']
                sheets = rep_info['sheets']
                k_sheets = len(sheets)
                start_rep_row = current_row
                fill = zebra_fill if rep_idx % 2 == 0 else PatternFill(fill_type=None)

                for k_idx, s_title in enumerate(sheets):
                    r = current_row
                    ws_toc.row_dimensions[r].height = 24

                    if k_idx == 0:
                        c1 = ws_toc.cell(row=r, column=1, value=rep_idx)
                        c1.alignment = Alignment(horizontal="center", vertical="center")
                        c2 = ws_toc.cell(row=r, column=2, value=t.name)
                        c2.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                        c3 = ws_toc.cell(row=r, column=3, value=t.period or "—")
                        c3.alignment = Alignment(horizontal="center", vertical="center")
                        c4 = ws_toc.cell(row=r, column=4, value=subs_cnt)
                        c4.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        ws_toc.cell(row=r, column=1, value="")
                        ws_toc.cell(row=r, column=2, value="")
                        ws_toc.cell(row=r, column=3, value="")
                        ws_toc.cell(row=r, column=4, value="")

                    c5 = ws_toc.cell(row=r, column=5, value=f"{s_title}")
                    c5.hyperlink = f"#'{s_title}'!A1"
                    c5.font = link_font
                    c5.alignment = Alignment(horizontal="left", vertical="center")

                    for col in range(1, 6):
                        cell = ws_toc.cell(row=r, column=col)
                        if fill.fill_type:
                            cell.fill = fill
                        cell.border = thin_border
                        if col != 5:
                            cell.font = td_font

                    current_row += 1

                if k_sheets > 1:
                    for merge_col in [1, 2, 3, 4]:
                        ws_toc.merge_cells(
                            start_row=start_rep_row,
                            start_column=merge_col,
                            end_row=start_rep_row + k_sheets - 1,
                            end_column=merge_col
                        )

            ws_toc.column_dimensions['A'].width = 8
            ws_toc.column_dimensions['B'].width = 50
            ws_toc.column_dimensions['C'].width = 25
            ws_toc.column_dimensions['D'].width = 18
            ws_toc.column_dimensions['E'].width = 38

        date_str = datetime.now().strftime("%d_%m_%Y")
        count_str = f"{len(items)}_отчетов" if len(items) > 1 else "отчет"
        filename = f"Сводный_пакет_{count_str}_{date_str}.xlsx"

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
                current_width = ws.column_dimensions[col_letter].width
                if current_width is None or adjusted_width > current_width:
                    ws.column_dimensions[col_letter].width = adjusted_width
                
        # Авто-высота строк
        for row in ws.rows:
            if not row:
                continue
            max_lines = 1
            is_header = (row[0].row <= 2) # Добавим отступ для шапки
            
            for cell in row:
                if cell.value:
                    try:
                        col_letter = get_column_letter(cell.column)
                        col_width = ws.column_dimensions[col_letter].width
                        if not col_width:
                            col_width = min_col_width
                        
                        # Эффективная ширина символов (с учетом переносов слов и жирного шрифта)
                        effective_width = max(5, int(col_width) * 0.8)
                        
                        lines = str(cell.value).split("\n")
                        total_lines_for_cell = 0
                        for line in lines:
                            if len(line) == 0:
                                total_lines_for_cell += 1
                            else:
                                total_lines_for_cell += -(-len(line) // int(effective_width))
                                
                        if total_lines_for_cell > max_lines:
                            max_lines = total_lines_for_cell
                    except:
                        pass
                        
            # Если это первая строка (объединенная), она обычно длинная, но занимает много колонок
            if row[0].row == 1:
                ws.row_dimensions[row[0].row].height = 25
            else:
                padding = 15 if is_header else 5
                ws.row_dimensions[row[0].row].height = max_lines * default_row_height + padding

    @staticmethod
    def normalize_org_name(name):
        """
        Нормализует наименование учреждения для надежного сопоставления:
        - приведение к нижнему регистру
        - удаление кавычек («, », ", ', `)
        - замена буквы 'ё' на 'е'
        - замена неразрывных пробелов и сжатие пробельных последовательностей
        """
        if not name:
            return ""
        clean = re.sub(r'[\'\"«»„“”`]', '', str(name)).lower()
        clean = clean.replace('ё', 'е').replace('\xa0', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    @staticmethod
    def parse_summary_excel(file_stream_or_path, template):
        """
        Разбирает отредактированный Excel файл сводной таблицы (выгруженный через export_report).
        Сопоставляет данные учреждений и колонок, находит все различия с текущей БД.
        Поддерживает:
        - Гибридную идентификацию учреждений (скрытая колонка B с user_id + fallback по наименованию).
        - Гибридную идентификацию колонок (комментарии field_key + наименования заголовков + порядок).
        - Полную синхронизацию (пустая ячейка/тире означает сброс значения).
        - Авто-пропуск строк итогов (Итого, Итого по организации, [Группа] всего, заголовки подгрупп).
        - Многострочные отчеты (is_multiple).
        """
        from app.models import User, ReportSubmission
        from app.utils import build_table_headers

        try:
            wb = openpyxl.load_workbook(file_stream_or_path, data_only=True)
        except Exception as e:
            return {
                'success': False,
                'error': f'Не удалось открыть Excel файл: {str(e)}'
            }

        # 1. Загружаем пользователей и строим словари соответствий
        all_users = User.query.all()
        users_by_id = {u.id: u for u in all_users}
        users_by_desc = {}
        users_by_username = {}

        for u in all_users:
            if u.description:
                users_by_desc[ExcelService.normalize_org_name(u.description)] = u
            if u.username:
                users_by_username[ExcelService.normalize_org_name(u.username)] = u

        # 2. Загружаем существующие сданные отчеты для этого шаблона
        existing_submissions = ReportSubmission.query.filter_by(template_id=template.id).all()
        subs_by_user_id = {s.user_id: s for s in existing_submissions}

        all_diffs = []
        warnings = []
        matched_user_ids = set()

        schema = template.schema if isinstance(template.schema, list) else json.loads(template.schema or '[]')

        for sheet_idx, sheet_data in enumerate(schema):
            clean_title = re.sub(r'[\\*?:/\[\]]', '', str(sheet_data.get('sheet_title', ''))).strip()[:31]

            # Ищем лист в файле: сначала по точному имени, затем case-insensitive, затем по индексу
            ws = None
            if clean_title in wb.sheetnames:
                ws = wb[clean_title]
            else:
                for sname in wb.sheetnames:
                    if sname.strip().lower() == clean_title.lower():
                        ws = wb[sname]
                        break
            if not ws and sheet_idx < len(wb.worksheets):
                ws = wb.worksheets[sheet_idx]
                warnings.append(f'Лист "{clean_title}" не найден по имени, использован лист #{sheet_idx + 1} ("{ws.title}").')

            if not ws:
                warnings.append(f'Лист "{clean_title}" отсутствует в файле — пропущен.')
                continue

            fields = sheet_data.get('fields', [])
            header_rows, leaf_fields = build_table_headers(fields)
            max_depth = len(header_rows) if header_rows else 1

            # Поиск строки шапки (где в столбце A написано "Организация")
            header_start_row = 2
            for r in range(1, min(10, (ws.max_row or 1) + 1)):
                val = ws.cell(row=r, column=1).value
                if val and 'организац' in str(val).lower():
                    header_start_row = r
                    break

            header_bottom_row = header_start_row + max_depth - 1

            # Определяем, есть ли скрытый столбец ID в колонке B
            is_col_b_id = False
            col_b_val = ws.cell(row=header_bottom_row, column=2).value
            if col_b_val and str(col_b_val).strip().lower() in ['id', '_id', '_user_id', 'ид']:
                is_col_b_id = True
            elif ws.column_dimensions['B'].hidden:
                is_col_b_id = True
            else:
                # Проверим первые строки с данными: числовое ли значение в B, равное ID пользователя
                for test_r in range(header_bottom_row + 1, min(header_bottom_row + 6, (ws.max_row or 1) + 1)):
                    test_b = ws.cell(row=test_r, column=2).value
                    if test_b is not None:
                        try:
                            tid = int(test_b)
                            if tid in users_by_id:
                                is_col_b_id = True
                                break
                        except (ValueError, TypeError):
                            pass

            id_col = 2 if is_col_b_id else None
            data_start_col = 3 if is_col_b_id else 2

            # Построим словарь понятных названий для каждого поля
            field_display_names = {}
            for f in fields:
                fk = f.get('name') or f.get('id')
                if fk:
                    field_display_names[fk] = f.get('label', fk)

            def get_friendly_field_label(f_item):
                fk = f_item.get('name') or f_item.get('id')
                leaf_lbl = f_item.get('label', fk)
                orig_lbl = field_display_names.get(fk)
                if orig_lbl and orig_lbl != leaf_lbl:
                    if leaf_lbl and orig_lbl in leaf_lbl:
                        return leaf_lbl
                    return f"{orig_lbl} ({leaf_lbl})"
                return leaf_lbl or fk

            # Сопоставление колонок листа с полями схемы
            col_to_field = {}
            for col_idx in range(data_start_col, (ws.max_column or 0) + 1):
                field_match = None

                # 1. Проверяем комментарии по всей высоте шапки в данной колонке
                for hr in range(header_start_row, header_bottom_row + 1):
                    h_cell = ws.cell(row=hr, column=col_idx)
                    if h_cell.comment and h_cell.comment.text:
                        m = re.search(r'field_key:([^\s\r\n]+)', h_cell.comment.text)
                        if m:
                            fk = m.group(1).strip()
                            for f in leaf_fields:
                                if (f.get('name') or f.get('id')) == fk:
                                    field_match = f
                                    break
                    if field_match:
                        break

                # 2. Позиционное соответствие (основной детерминированный механизм для выгрузок ЦОПП: 1-к-1 с leaf_fields)
                f_idx = col_idx - data_start_col
                if not field_match and 0 <= f_idx < len(leaf_fields):
                    field_match = leaf_fields[f_idx]

                # 3. Fallback: поиск по уникальному тексту заголовка (только если имя уникально среди leaf_fields!)
                if not field_match:
                    header_val = ws.cell(row=header_bottom_row, column=col_idx).value
                    if not header_val:
                        for hr in range(header_bottom_row - 1, header_start_row - 1, -1):
                            hv = ws.cell(row=hr, column=col_idx).value
                            if hv:
                                header_val = hv
                                break
                    if header_val:
                        norm_label = ExcelService.normalize_org_name(header_val)
                        matching_fields = [f for f in leaf_fields if ExcelService.normalize_org_name(f.get('label')) == norm_label]
                        if len(matching_fields) == 1:
                            field_match = matching_fields[0]

                if field_match:
                    col_to_field[col_idx] = field_match

            if not col_to_field:
                warnings.append(f'На листе "{ws.title}" не удалось сопоставить колонки показателей.')
                continue

            # Чтение строк с данными
            current_user = None
            user_rows = {} # uid -> list of dict {col_idx: cell_value}
            
            for r in range(header_bottom_row + 1, (ws.max_row or 0) + 1):
                val_a = ws.cell(row=r, column=1).value
                val_b = ws.cell(row=r, column=id_col).value if id_col else None

                # Проверка пустой строки
                is_row_empty = True
                if val_a is not None and str(val_a).strip() != '':
                    is_row_empty = False
                else:
                    for c in col_to_field:
                        cv = ws.cell(row=r, column=c).value
                        if cv not in [None, '', '-', '—']:
                            is_row_empty = False
                            break
                if is_row_empty:
                    continue

                # Проверка служебных строк
                if val_a is not None and str(val_a).strip() != '':
                    str_a = str(val_a).strip()
                    lower_a = str_a.lower()

                    # Итого или Итого по организации
                    if lower_a == 'итого' or lower_a.startswith('итого по организации'):
                        current_user = None
                        continue

                    # Промежуточный итог подгруппы (заканчивается на "всего")
                    norm_a = ExcelService.normalize_org_name(str_a)
                    if lower_a.endswith('всего') and norm_a not in users_by_desc and norm_a not in users_by_username:
                        current_user = None
                        continue

                    # Проверяем, не является ли это строкой заголовка подгруппы
                    if norm_a not in users_by_desc and norm_a not in users_by_username:
                        data_empty = all(ws.cell(row=r, column=c).value in [None, '', '-', '—'] for c in col_to_field)
                        if data_empty:
                            current_user = None
                            continue

                # Идентификация учреждения
                detected_user = None
                if id_col and val_b is not None and str(val_b).strip() != '':
                    try:
                        uid = int(val_b)
                        if uid in users_by_id:
                            detected_user = users_by_id[uid]
                    except (ValueError, TypeError):
                        pass

                if not detected_user and val_a is not None and str(val_a).strip() != '':
                    norm_a = ExcelService.normalize_org_name(val_a)
                    if norm_a in users_by_desc:
                        detected_user = users_by_desc[norm_a]
                    elif norm_a in users_by_username:
                        detected_user = users_by_username[norm_a]

                if detected_user:
                    current_user = detected_user
                    matched_user_ids.add(current_user.id)
                elif val_a is None or str(val_a).strip() == '':
                    # Объединенная ячейка (продолжение предыдущего пользователя в многострочном ответе)
                    pass
                else:
                    norm_a = ExcelService.normalize_org_name(val_a)
                    if norm_a not in ['итого', 'всего'] and not norm_a.endswith('всего'):
                        warnings.append(f'Лист "{ws.title}", строка {r}: учреждение "{val_a}" не найдено в базе данных — строка пропущена.')
                    current_user = None
                    continue

                if not current_user:
                    continue

                # Считываем ячейки строки
                row_cells = {}
                for c, field in col_to_field.items():
                    row_cells[c] = ws.cell(row=r, column=c).value

                if current_user.id not in user_rows:
                    user_rows[current_user.id] = []
                user_rows[current_user.id].append(row_cells)

            # Сопоставление с базой данных и формирование списка изменений
            for uid, rows_list in user_rows.items():
                user = users_by_id[uid]
                sub = subs_by_user_id.get(uid)
                old_data = sub.data.copy() if (sub and sub.data) else {}

                for c, field in col_to_field.items():
                    f_key = field.get('name') or field.get('id')
                    f_label = get_friendly_field_label(field)
                    f_type = str(field.get('type', '')).lower()
                    is_numeric = f_type in ['number', 'числовое']
                    is_multiple = field.get('is_multiple', False) or len(rows_list) > 1

                    old_val = old_data.get(f_key)

                    if not is_multiple:
                        raw_cell_val = rows_list[0][c]
                        if raw_cell_val in [None, '', '-', '—']:
                            new_val = None
                        elif is_numeric:
                            try:
                                num_str = str(raw_cell_val).replace(' ', '').replace(',', '.')
                                num_float = float(num_str)
                                new_val = int(num_float) if num_float.is_integer() else round(num_float, 2)
                            except (ValueError, TypeError):
                                new_val = str(raw_cell_val).strip()
                        else:
                            new_val = str(raw_cell_val).strip()

                        # Сравнение старого и нового значения
                        is_diff = False
                        if old_val != new_val:
                            if old_val in [None, '', '-', '—'] and new_val in [None, '', '-', '—']:
                                is_diff = False
                            elif is_numeric and old_val not in [None, '', '-', '—'] and new_val not in [None, '', '-', '—']:
                                try:
                                    if float(old_val) == float(new_val):
                                        is_diff = False
                                    else:
                                        is_diff = True
                                except Exception:
                                    is_diff = True
                            elif not is_numeric:
                                str_old = str(old_val).strip() if old_val not in [None, '', '-', '—'] else ""
                                str_new = str(new_val).strip() if new_val not in [None, '', '-', '—'] else ""
                                is_diff = (str_old != str_new)
                            else:
                                is_diff = True

                        if is_diff:
                            all_diffs.append({
                                'user_id': uid,
                                'org_name': user.description or user.username,
                                'sheet_title': sheet_data.get('sheet_title', 'Лист'),
                                'field_name': f_key,
                                'field_label': f_label,
                                'old_val': old_val,
                                'new_val': new_val,
                                'old_val_display': "-" if old_val in [None, '', '-', '—'] else str(old_val),
                                'new_val_display': "-" if new_val in [None, '', '-', '—'] else str(new_val),
                                'is_multiple': False
                            })
                    else:
                        # Многострочные значения
                        new_list = []
                        has_any = False
                        for r_dict in rows_list:
                            raw_val = r_dict[c]
                            if raw_val in [None, '', '-', '—']:
                                item_val = ""
                            elif is_numeric:
                                try:
                                    num_str = str(raw_val).replace(' ', '').replace(',', '.')
                                    num_float = float(num_str)
                                    item_val = int(num_float) if num_float.is_integer() else round(num_float, 2)
                                    has_any = True
                                except (ValueError, TypeError):
                                    item_val = str(raw_val).strip()
                                    has_any = True
                            else:
                                item_val = str(raw_val).strip()
                                has_any = True
                            new_list.append(item_val)

                        new_val = new_list if has_any else []
                        old_list = old_val if isinstance(old_val, list) else ([old_val] if old_val not in [None, ''] else [])

                        # Сравниваем списки (исключая пустые/тире элементы)
                        clean_new = [str(x).strip() for x in new_val if x not in [None, '', '-', '—']]
                        clean_old = [str(x).strip() for x in old_list if x not in [None, '', '-', '—']]

                        if clean_old != clean_new:
                            all_diffs.append({
                                'user_id': uid,
                                'org_name': user.description or user.username,
                                'sheet_title': sheet_data.get('sheet_title', 'Лист'),
                                'field_name': f_key,
                                'field_label': f_label,
                                'old_val': old_val,
                                'new_val': new_val,
                                'old_val_display': ", ".join(clean_old) if clean_old else "-",
                                'new_val_display': ", ".join(clean_new) if clean_new else "-",
                                'is_multiple': True
                            })

        return {
            'success': True,
            'diffs': all_diffs,
            'total_changes': len(all_diffs),
            'changed_orgs_count': len(set(d['user_id'] for d in all_diffs)),
            'total_orgs_found': len(matched_user_ids),
            'warnings': warnings
        }

    @staticmethod
    def apply_summary_changes(template, diffs):
        """
        Применяет список проверенных изменений в базе данных (ReportSubmission).
        Возвращает (количество измененных полей, количество обновленных учреждений).
        """
        from app.models import ReportSubmission
        from app.extensions import db

        user_updates = {}
        for d in diffs:
            uid = d['user_id']
            if uid not in user_updates:
                user_updates[uid] = {}
            user_updates[uid][d['field_name']] = d['new_val']

        for uid, fields_dict in user_updates.items():
            sub = ReportSubmission.query.filter_by(template_id=template.id, user_id=uid).first()
            if not sub:
                sub = ReportSubmission(template_id=template.id, user_id=uid, data={})
                db.session.add(sub)

            data_copy = sub.data.copy() if sub.data else {}
            for fname, nval in fields_dict.items():
                if nval is None:
                    # Режим полной синхронизации: сброс значения
                    data_copy[fname] = None
                else:
                    data_copy[fname] = nval

            sub.data = data_copy

        db.session.commit()
        return len(diffs), len(user_updates)
