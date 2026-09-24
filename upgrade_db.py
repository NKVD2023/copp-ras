"""
upgrade_db.py — Скрипт безопасной миграции базы данных.
Запуск вручную:
    python upgrade_db.py

Что делает:
1. Создает недостающие таблицы (departments, department_templates, background_tasks и др.)
2. Проверяет наличие всех колонок в существующих таблицах через PRAGMA table_info.
3. Добавляет отсутствующие колонки (department_id, ip_address, is_template и др.) без потери данных.
4. Проверяет работоспособность выборки пользователей.
"""
import os
import sys
import sqlite3
from config import basedir

def get_columns(cursor, table_name):
    """Возвращает множество имен колонок таблицы."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cursor.fetchall()}
    except Exception:
        return set()

def upgrade_database():
    print("=" * 60)
    print("  МИГРАЦИЯ БАЗЫ ДАННЫХ COPP-RAS")
    print("=" * 60)

    # 1. Сначала используем контекст Flask для создания всех новых таблиц
    try:
        from app import create_app
        from app.extensions import db
        app = create_app()
        with app.app_context():
            db.create_all()
            print("[OK] Новые таблицы (если отсутствовали) успешно созданы через SQLAlchemy.")
    except Exception as e:
        print(f"[WARN] Ошибка при создании таблиц через SQLAlchemy: {e}")

    # 2. Прямая работа с файлом SQLite для добавления недостающих колонок
    db_path = os.path.join(basedir, 'reports.db')
    if not os.path.exists(db_path):
        print(f"[!] Файл базы данных не найден по пути: {db_path}")
        print("    Если используется другое имя файла или путь, проверьте config.py")
        return False

    print(f"[*] Подключение к базе данных: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Описание необходимых колонок для проверки:
    # (таблица, колонка, sql_тип_и_параметры)
    columns_to_check = [
        ('users', 'department_id', 'INTEGER REFERENCES departments(id)'),
        ('users', 'group', 'VARCHAR(50)'),
        ('uploaded_files', 'department_id', 'INTEGER REFERENCES departments(id)'),
        ('dictionaries', 'department_id', 'INTEGER REFERENCES departments(id)'),
        ('action_logs', 'ip_address', 'VARCHAR(45)'),
        ('report_templates', 'period_data', 'JSON'),
        ('report_templates', 'is_template', 'BOOLEAN DEFAULT 0'),
        ('report_templates', 'short_name', 'VARCHAR(64)'),
        ('report_submissions', 'is_revision', 'BOOLEAN DEFAULT 0'),
        ('report_submissions', 'revision_comment', 'TEXT'),
        ('report_submissions', 'returned_at', 'DATETIME'),
        ('report_submissions', 'returned_by_id', 'INTEGER REFERENCES users(id)'),
    ]

    changes_applied = 0

    for table, column, col_def in columns_to_check:
        cols = get_columns(cursor, table)
        if not cols:
            print(f"[SKIP] Таблица '{table}' пока не существует, пропускаем.")
            continue

        if column in cols:
            print(f"[OK]   Таблица '{table}': колонка '{column}' уже существует.")
        else:
            alter_query = f"ALTER TABLE {table} ADD COLUMN {column} {col_def};"
            try:
                cursor.execute(alter_query)
                conn.commit()
                print(f"[+]   Таблица '{table}': УСПЕШНО добавлена колонка '{column}'.")
                changes_applied += 1
            except Exception as err:
                print(f"[ERR] Ошибка при добавлении {table}.{column}: {err}")

    conn.close()

    # 3. Тестовая проверка ORM-запроса к модели User и инициализация настроек
    print("-" * 60)
    print("[*] Проверка чтения модели User и настроек через SQLAlchemy...")
    try:
        with app.app_context():
            from app.models import User, MaintenanceSetting
            count = User.query.count()
            sample_user = User.query.first()
            user_info = f"'{sample_user.username}', отдел: {sample_user.department_id}" if sample_user else "нет записей"
            print(f"[OK] Пользователей в базе: {count} (пример: {user_info}).")

            # Инициализируем запись настроек техработ, если еще нет
            setting = MaintenanceSetting.get_settings()
            print(f"[OK] Таблица maintenance_settings готова (статус активности: {setting.is_active}).")
    except Exception as e:
        print(f"[ERR] Ошибка при проверке чтения данных: {e}")
        return False

    print("=" * 60)
    print(f"  ГОТОВО! Применено изменений: {changes_applied}. База данных актуальна.")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = upgrade_database()
    sys.exit(0 if success else 1)
