import sqlite3
import os
import sys

# Путь к БД
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports.db')

def upgrade():
    if not os.path.exists(DB_PATH):
        print(f"База данных {DB_PATH} не найдена. Пропуск миграции.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем наличие колонки 'group' в таблице 'users'
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'group' not in columns:
        print("Добавление колонки 'group' в таблицу 'users'...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN \"group\" VARCHAR(50)")
            conn.commit()
            print("Колонка 'group' успешно добавлена.")
        except Exception as e:
            print(f"Ошибка при добавлении колонки: {e}")
            sys.exit(1)
    else:
        print("Колонка 'group' уже существует в таблице 'users'.")
        
    conn.close()

if __name__ == '__main__':
    upgrade()
