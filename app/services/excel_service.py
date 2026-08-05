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
        header_cell.fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
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
        header_fill = PatternFill("solid", fgColor="0071DC")
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
                row_data = [org_name]
                
                # Идем только по leaf_fields (те, которые реально заполнялись)
                for f in leaf_fields:
                    # Поддержка старых имен 'name' или 'id'
                    field_key = f.get('name') or f.get('id')
                    
                    val = sub.data.get(field_key, '-')
                    
                    # Если значение является списком (например, для динамических полей), объединяем его в строку
                    if isinstance(val, list):
                        val = "\n".join([str(v) for v in val if v is not None and str(v).strip() != ''])
                        if val == "":
                            val = "-"
                    
                    # Учет старых типов и новых
                    f_type = str(f.get('type', '')).lower()
                    if f_type in ['number', 'числовое'] and val not in ['-', '', None]:
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            pass
                    row_data.append(val)

                ws.append(row_data)
                ws.row_dimensions[current_row].height = 40 

                for col_idx, _ in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx == 1 else align_center
                
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
                            try:
                                col_total += float(val)
                                has_data = True
                            except ValueError:
                                pass
                    total_row.append(col_total if has_data else 0)
                else:
                    total_row.append('-')

            ws.append(total_row)
            ws.row_dimensions[current_row].height = 30
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
