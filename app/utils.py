"""
Вспомогательные утилиты приложения (Core).
Содержит функции, которые могут использоваться во всех модулях системы.
"""
from flask_login import current_user
from flask import request
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
    
    ip = None
    try:
        # Пытаемся получить IP-адрес (с учетом того, что сервер может быть за прокси)
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
    except Exception:
        pass # Игнорируем ошибку, если функция вызвана вне контекста запроса (например, в фоне)

    log_entry = ActionLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка логирования: {e}")

def is_mobile(req) -> bool:
    """
    Проверяет, является ли устройство мобильным на основе заголовка User-Agent.
    """
    user_agent = req.headers.get('User-Agent', '').lower()
    mobile_patterns = [
        'android', 'webos', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'mobile'
    ]
    return any(pattern in user_agent for pattern in mobile_patterns)
