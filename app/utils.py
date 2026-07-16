"""
Вспомогательные утилиты приложения (Core).
Содержит функции, которые могут использоваться во всех модулях системы.
"""
from flask_login import current_user
from app import db
from app.models import ActionLog

def log_action(action: str, details: str = ""):
    """
    Утилита для логирования действий пользователей (аудит).
    Привязывает действие к текущему авторизованному пользователю, если он есть,
    или помечает как системное действие, если пользователя нет в контексте.

    :param action: Краткое описание действия (например, 'Вход', 'Удаление').
    :param details: Подробности (например, 'Пользователь admin удалил отчет #5').
    """
    # Получаем ID пользователя, только если контекст авторизации существует
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    log_entry = ActionLog(
        user_id=user_id,
        action=action,
        details=details
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка логирования: {e}")
