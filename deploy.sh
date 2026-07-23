#!/bin/bash

echo "🚀 Этап 1: Отправка изменений на GitHub..."
git add .
git commit -m "feat: redesign reports tabs, add template logic and fast publishing"
git push origin main

echo "🚀 Этап 2: Подключение к боевому серверу и обновление..."
# Подключаемся по SSH, переходим в папку, обновляем БД и запускаем ваш скрипт update
ssh ras.copp@ras.copp82.ru << 'EOF'
cd /var/www/copp-ras

echo "📦 Обновление структуры базы данных..."
# Эта команда добавит нужную колонку в БД. Если колонка уже есть (например, при повторном запуске), скрипт просто пойдет дальше (благодаря || true).
python3 -c "import sqlite3; conn = sqlite3.connect('reports.db'); conn.execute('ALTER TABLE report_templates ADD COLUMN is_template BOOLEAN DEFAULT 0;'); conn.commit(); conn.close()" || true

echo "🔄 Запуск скрипта обновления на сервере..."
# Запускаем скрипт update, который лежит на сервере
bash update
EOF

echo "✅ Деплой успешно завершен!"
