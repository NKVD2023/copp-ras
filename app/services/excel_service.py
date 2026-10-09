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
        max_col = len(leaf_fields) + 1

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

        ws.column_dimensions['A'].width = 50
        for col_idx in range(2, max_col + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 25

        # 3. ДАННЫЕ
        current_row = start_row + max_depth

        for sub in submissions:
            org_name = sub.user.description if sub.user.description else sub.user.username

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

            if max_len > 1:
                ws.merge_cells(start_row=start_merge_row, start_column=1, end_row=start_merge_row + max_len - 1, end_column=1)

                col_idx = 2
                for f in leaf_fields:
                    field_key = f.get('name') or f.get('id')
                    val = sub.data.get(field_key)
                    if not isinstance(val, list):
                        ws.merge_cells(start_row=start_merge_row, start_column=col_idx, end_row=start_merge_row + max_len - 1, end_column=col_idx)
                    col_idx += 1

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

        ExcelService._autosize_excel(ws)

        for col_idx in range(1, max_col + 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = thin_border
            cell.alignment = align_left if col_idx == 1 else align_center

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
