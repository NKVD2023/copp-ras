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
        ws.append(["Организация"])
        
        for d in debtors:
            org_name = d.description if d.description else d.username
            ws.append([org_name])
            
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Должники_{template.short_name}.xlsx".replace(" ", "_")
        return output, filename

    @staticmethod
    def export_report(template, submissions):
        """
        Формирует сводный Excel файл со сданными отчетами.
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

            # Вычисляем количество колонок
            max_col = len(sheet_data['fields']) + 1

            # 1. ЗАГОЛОВОК (Полное наименование отчета)
            title_cell = ws.cell(row=1, column=1, value=template.name)
            title_cell.font = title_font
            title_cell.alignment = align_center
            
            # Рисуем рамку для всего заголовка
            for col in range(1, max_col + 1):
                ws.cell(row=1, column=col).border = thin_border
                
            # Объединяем ячейки для заголовка
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
            ws.row_dimensions[1].height = 100 # Высокая строка для заголовка

            # 2. ШАПКА ТАБЛИЦЫ
            headers = ['Организация'] + [f['label'] for f in sheet_data['fields']]
            ws.append(headers) # Автоматически добавится на 2-ю строку
            ws.row_dimensions[2].height = 100

            # Ширина колонок
            ws.column_dimensions['A'].width = 50 
            for col_idx in range(2, max_col + 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = 45

            # Стилизуем шапку
            for col_idx, _ in enumerate(headers, 1):
                cell = ws.cell(row=2, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = align_center
                cell.border = thin_border

            # 3. ДАННЫЕ
            current_row = 3
            for sub in submissions:
                org_name = sub.user.description if sub.user.description else sub.user.username
                row_data = [org_name]
                for f in sheet_data['fields']:
                    val = sub.data.get(f['name'], '-')
                    if f['type'] == 'number' and val not in ['-', '', None]:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                    row_data.append(val)

                ws.append(row_data)
                ws.row_dimensions[current_row].height = 70 

                for col_idx, _ in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                    cell.alignment = align_left if col_idx == 1 else align_center
                
                current_row += 1

            # 4. ИТОГО
            total_row = ['Итого']
            for f in sheet_data['fields']:
                if f['type'] == 'number':
                    col_total = 0
                    has_data = False
                    for sub in submissions:
                        val = sub.data.get(f['name'])
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
            ws.row_dimensions[current_row].height = 40
            
            for col_idx, _ in enumerate(total_row, 1):
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
