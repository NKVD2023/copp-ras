"""
Сервис для построения stat_schema (данных статистики) для экспорта в Excel.
Инкапсулирует логику сбора данных из ReportTemplate + ReportSubmission,
используя build_table_headers() для корректной обработки иерархической схемы полей.
"""
from app.utils import build_table_headers
from app.models import ReportSubmission


class StatService:

    @staticmethod
    def build_unified_stat_schema(matched_templates, user_id):
        """
        Строит единую stat_schema для вывода на дашборде и выгрузки в Excel.
        Возвращает список листов (вкладок), где каждый лист содержит:
        - header_rows: сложная структура заголовков для colspan/rowspan
        - leaf_fields: плоские поля
        - periods_data: список данных по периодам
        """
        if not matched_templates:
            return None

        # Ожидаем, что matched_templates отсортированы по убыванию (новые сверху)
        latest_template = matched_templates[0]
        
        import copy
        stat_schema = copy.deepcopy(latest_template.schema) or []
        
        for sheet in stat_schema:
            fields = sheet.get('fields', [])
            header_rows, leaf_fields = build_table_headers(fields)
            sheet['header_rows'] = header_rows
            sheet['leaf_fields'] = leaf_fields
            sheet['periods_data'] = []
            
        for template in matched_templates:
            submission = ReportSubmission.query.filter_by(template_id=template.id, user_id=user_id).first()
            period_name = template.period or f"Период {template.id}"
            
            for sheet in stat_schema:
                sheet_data = {
                    'period': period_name,
                    'template_id': template.id,
                    'has_submission': submission is not None,
                    'values': submission.data if submission else {}
                }
                sheet['periods_data'].append(sheet_data)
                
        # Рассчитываем дельты (разницу) между текущим и предыдущим периодом
        for sheet in stat_schema:
            periods_data = sheet['periods_data']
            # Т.к. сортировка по убыванию, [i+1] — это предыдущий (более старый) период
            for i in range(len(periods_data) - 1):
                curr = periods_data[i]
                prev = periods_data[i+1]
                if curr['has_submission'] and prev['has_submission']:
                    curr['deltas'] = {}
                    for field in sheet['leaf_fields']:
                        f_id = str(field.get('name') or field.get('id', ''))
                        if not f_id: continue
                        if field.get('type') == 'number':
                            cv_raw = curr['values'].get(f_id)
                            pv_raw = prev['values'].get(f_id)
                            try:
                                cv = float(cv_raw) if cv_raw not in [None, ""] else 0.0
                                pv = float(pv_raw) if pv_raw not in [None, ""] else 0.0
                                curr['deltas'][f_id] = cv - pv
                            except (ValueError, TypeError):
                                pass

        return stat_schema
