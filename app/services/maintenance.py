"""
app/services/maintenance.py — Логика и состояние режима технических работ.
"""
from datetime import datetime, timedelta
from app.models.settings import MaintenanceSetting

def get_maintenance_status() -> dict:
    """
    Возвращает актуальный статус технических работ.
    Все даты в БД хранятся в UTC, возвращаются также с форматированием в МСК (UTC+3).
    """
    try:
        setting = MaintenanceSetting.get_settings()
        now_utc = datetime.utcnow()
        now_msk = now_utc + timedelta(hours=3)

        in_maintenance = False
        is_scheduled = False
        is_scheduled_soon = False
        remaining_seconds = 0

        # 1. Принудительное ручное включение
        if setting.is_active:
            in_maintenance = True

        # 2. Проверка по расписанию
        if setting.start_at and setting.end_at:
            if setting.start_at <= now_utc <= setting.end_at:
                in_maintenance = True
                remaining_seconds = max(0, int((setting.end_at - now_utc).total_seconds()))
            elif now_utc < setting.start_at:
                is_scheduled = True
                # Предупреждать за 24 часа до старта
                if setting.start_at - now_utc <= timedelta(hours=24):
                    is_scheduled_soon = True

        # Человекопонятный компактный формат расписания (одна дата и время от и до)
        schedule_text = ''
        if setting.start_at and setting.end_at:
            start_dt = setting.start_at + timedelta(hours=3)
            end_dt = setting.end_at + timedelta(hours=3)
            if start_dt.date() == end_dt.date():
                schedule_text = f"{start_dt.strftime('%d.%m.%Y')} с {start_dt.strftime('%H:%M')} до {end_dt.strftime('%H:%M')} (МСК)"
            else:
                schedule_text = f"с {start_dt.strftime('%d.%m.%Y %H:%M')} по {end_dt.strftime('%d.%m.%Y %H:%M')} (МСК)"
        elif setting.start_at:
            start_dt = setting.start_at + timedelta(hours=3)
            schedule_text = f"{start_dt.strftime('%d.%m.%Y')} с {start_dt.strftime('%H:%M')} (МСК)"

        # Форматирование для отображения в шаблонах
        start_msk_str = (setting.start_at + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M') if setting.start_at else ''
        end_msk_str = (setting.end_at + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M') if setting.end_at else ''

        # Значения для полей формы <input type="datetime-local">
        start_input = (setting.start_at + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M') if setting.start_at else ''
        end_input = (setting.end_at + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M') if setting.end_at else ''

        return {
            'is_active_toggle': bool(setting.is_active),
            'in_maintenance': in_maintenance,
            'is_scheduled': is_scheduled,
            'is_scheduled_soon': is_scheduled_soon,
            'schedule_text': schedule_text,
            'start_msk': start_msk_str,
            'end_msk': end_msk_str,
            'start_input': start_input,
            'end_input': end_input,
            'message': setting.message or "Проводятся плановые технические работы. Приносим извинения за временные неудобства.",
            'remaining_seconds': remaining_seconds,
            'now_msk': now_msk.strftime('%d.%m.%Y %H:%M'),
        }
    except Exception as e:
        # При ошибке базы данных не блокируем работу сайта
        return {
            'is_active_toggle': False,
            'in_maintenance': False,
            'is_scheduled': False,
            'is_scheduled_soon': False,
            'schedule_text': '',
            'start_msk': '',
            'end_msk': '',
            'start_input': '',
            'end_input': '',
            'message': 'Проводятся плановые технические работы.',
            'remaining_seconds': 0,
            'now_msk': '',
        }
