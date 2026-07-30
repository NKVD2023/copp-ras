import os
from app import create_app, db

app = create_app()

with app.app_context():
    print("Проверка наличия колонки is_completed в таблице report_templates...")
    try:
        db.session.execute(db.text("ALTER TABLE report_templates ADD COLUMN is_completed BOOLEAN DEFAULT 0;"))
        db.session.commit()
        print("Колонка is_completed успешно добавлена в базу данных!")
    except Exception as e:
        db.session.rollback()
        if "duplicate column name" in str(e).lower():
            print("Колонка is_completed уже существует.")
        else:
            print("ВНИМАНИЕ! Не удалось создать колонку. Ошибка:", str(e))
