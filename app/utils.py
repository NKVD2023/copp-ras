from flask_login import current_user
from app import db
from app.models import ActionLog

def log_action(action, details=""):
    """
    Утилита для логирования действий пользователей.
    Привязывает действие к текущему авторизованному пользователю.
    """
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
