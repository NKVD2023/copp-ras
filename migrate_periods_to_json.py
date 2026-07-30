import re
import json
from app import create_app, db
from app.models import ReportTemplate

def parse_period(period_str):
    if not period_str or period_str in ('None', '1', '2', ''):
        return None

    period_str = period_str.strip()

    # 1. Квартал (например: "I квартал 2026", "за 3 квартал 2026")
    match = re.search(r'(I{1,3}V?|IV|1|2|3|4)\s*квартал\s*(\d{4})', period_str, re.IGNORECASE)
    if match:
        q_map = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}
        q = match.group(1).upper()
        if q in q_map:
            q = q_map[q]
        year = int(match.group(2))
        return {"type": "quarter", "quarter": q, "year": year}

    # 2. Неделя (например: "Неделя с 30.07.2026 по 06.08.2026")
    match = re.search(r'Неделя с\s*(\d{2}\.\d{2}\.\d{4})\s*по\s*(\d{2}\.\d{2}\.\d{4})', period_str, re.IGNORECASE)
    if match:
        # Неделя в новом формате сохраняется так же как start, end
        # Для input type="date" формат должен быть YYYY-MM-DD
        def to_iso(d):
            parts = d.split('.')
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return {"type": "week", "start": to_iso(match.group(1)), "end": to_iso(match.group(2))}

    # 3. Диапазон дат (например: "20.07.2026 - 25.07.2026")
    match = re.search(r'^(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})$', period_str)
    if match:
        def to_iso(d):
            parts = d.split('.')
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return {"type": "range", "start": to_iso(match.group(1)), "end": to_iso(match.group(2))}

    # 4. Конкретная дата (например: "22.07.2026")
    match = re.search(r'^(\d{2}\.\d{2}\.\d{4})$', period_str)
    if match:
        def to_iso(d):
            parts = d.split('.')
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return {"type": "date", "date": to_iso(match.group(1))}

    # 5. Месяц (например: "за июль 2026")
    months = {
        'январ': 'Январь', 'феврал': 'Февраль', 'март': 'Март', 'апрел': 'Апрель',
        'май': 'Май', 'ма': 'Май', 'июн': 'Июнь', 'июл': 'Июль', 'август': 'Август',
        'сентябр': 'Сентябрь', 'октябр': 'Октябрь', 'ноябр': 'Ноябрь', 'декабр': 'Декабрь'
    }
    match = re.search(r'([а-я]+)\s*(\d{4})', period_str, re.IGNORECASE)
    if match:
        word = match.group(1).lower()
        for k, v in months.items():
            if word.startswith(k):
                return {"type": "month", "month": v, "year": int(match.group(2))}

    # Не удалось распознать
    return None

app = create_app()

with app.app_context():
    print("Проверка наличия колонки period_data в таблице report_templates...")
    try:
        db.session.execute(db.text("ALTER TABLE report_templates ADD COLUMN period_data JSON;"))
        db.session.commit()
        print("Колонка period_data успешно добавлена в базу данных!")
    except Exception as e:
        db.session.rollback()
        if "duplicate column name" in str(e).lower():
            print("Колонка period_data уже существует.")
        else:
            print("ВНИМАНИЕ! Не удалось создать колонку. Ошибка:", str(e))

    print("Начало миграции старых периодов...")
    templates = ReportTemplate.query.all()
    migrated_count = 0
    skipped_count = 0
    already_migrated_count = 0

    for t in templates:
        if t.period_data is not None:
            already_migrated_count += 1
            continue
            
        parsed = parse_period(t.period)
        if parsed:
            t.period_data = parsed
            migrated_count += 1
            print(f"[{t.id}] Успешно: '{t.period}' -> {json.dumps(parsed, ensure_ascii=False)}")
        else:
            skipped_count += 1
            print(f"[{t.id}] Пропущено (не распознано): '{t.period}'")

    db.session.commit()
    print("-------------------------------------------------")
    print(f"Миграция завершена!")
    print(f"Уже были в новом формате: {already_migrated_count}")
    print(f"Успешно мигрировано: {migrated_count}")
    print(f"Пропущено (не распознано или пусто): {skipped_count}")
    print("Все изменения сохранены в БД.")
