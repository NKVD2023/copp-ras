#!/bin/bash

echo "🚀 Отправка изменений на GitHub..."
git add .
git commit -m "feat: Auto-fill organization name and fix MSK timezone"
git push origin main

echo "✅ Код успешно загружен в репозиторий!"
