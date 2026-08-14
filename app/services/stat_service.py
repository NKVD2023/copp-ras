"""
Сервис для построения stat_schema (данных статистики) для экспорта в Excel.
Инкапсулирует логику сбора данных из ReportTemplate + ReportSubmission,
используя build_table_headers() для корректной обработки иерархической схемы полей.
"""
from app.utils import build_table_headers
from app.models import ReportSubmission


class StatService:

    @staticmethod
    def build_stat_schema_for_export(assigned_templates, user_id):
        """
        Строит stat_schema для передачи в ExcelService.export_statistics().

        Использует build_table_headers() из utils.py для корректного извлечения
        листовых полей из иерархической схемы (аналогично логике дашборда).

        :param assigned_templates: список ReportTemplate, отсортированных по id ASC
        :param user_id: ID пользователя для поиска submissions
        :return: dict {"periods": [...], "fields": [...]} или None если шаблонов нет
        """
        if not assigned_templates:
            return None

        latest_template = assigned_templates[-1]
        schema = latest_template.schema or []

        stat_schema = {
            "periods": [],
            "fields": []
        }

        # 1) Собираем submissions для каждого шаблона одним проходом
        submissions_map = {}
        for t in assigned_templates:
            sub = ReportSubmission.query.filter_by(
                template_id=t.id, user_id=user_id
            ).first()
            submissions_map[t.id] = sub
            stat_schema["periods"].append({
                "period": t.period or f"Период {t.id}",
                "end_date": t.deadline.strftime("%d.%m.%Y") if t.deadline else "",
                "template_id": t.id,
            })

        # 2) Извлекаем листовые поля из каждого листа шаблона
        for sheet in schema:
            fields = sheet.get("fields", [])
            if not fields:
                continue

            _, leaf_fields = build_table_headers(fields)
            sheet_title = sheet.get("sheet_title", "")

            for field in leaf_fields:
                field_name = str(field.get("name") or field.get("id", ""))
                if not field_name:
                    continue

                field_type = field.get("type", "string")
                # Пропускаем нечисловые/неэкспортируемые типы
                if field_type in ["file", "comment"]:
                    continue

                label = field.get("label", field_name)
                # Добавляем префикс листа, если листов несколько
                if len(schema) > 1 and sheet_title:
                    label = f"{sheet_title} / {label}"

                row_data = {
                    "name": label,
                    "values": []
                }

                prev_value = None
                for t in assigned_templates:
                    sub = submissions_map[t.id]
                    val = None
                    has_data = False

                    if sub and sub.data and field_name in sub.data:
                        raw = sub.data[field_name]
                        if raw != "" and raw is not None:
                            val = raw
                            has_data = True

                    # Приведение к числу для расчёта дельты
                    current_num = None
                    if has_data and field_type in ["number", "float"]:
                        try:
                            current_num = float(val) if "." in str(val) else int(val)
                        except (ValueError, TypeError):
                            pass

                    delta = 0
                    status = "zero"
                    if current_num is not None and prev_value is not None:
                        delta = current_num - prev_value
                        if delta > 0:
                            status = "up"
                        elif delta < 0:
                            status = "down"

                    row_data["values"].append({
                        "value": val if has_data else "",
                        "has_data": has_data,
                        "delta": delta,
                        "status": status,
                        "type": field_type,
                    })

                    if current_num is not None:
                        prev_value = current_num

                stat_schema["fields"].append(row_data)

        return stat_schema
