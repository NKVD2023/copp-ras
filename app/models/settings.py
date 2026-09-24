"""
app/models/settings.py — Системные настройки (Технические работы и общие параметры).
"""
from app.extensions import db
from datetime import datetime

class MaintenanceSetting(db.Model):
    """
    Настройки режима технических работ.
    Все даты в базе хранятся в UTC.
    """
    __tablename__ = 'maintenance_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False)
    start_at = db.Column(db.DateTime, nullable=True)   # время начала в UTC
    end_at = db.Column(db.DateTime, nullable=True)     # время окончания в UTC
    message = db.Column(db.String(512), default="Проводятся плановые технические работы по обновлению системы. Приносим извинения за временные неудобства.")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls):
        """Получить текущую запись настроек или создать запись по умолчанию."""
        setting = cls.query.first()
        if not setting:
            setting = cls(is_active=False)
            db.session.add(setting)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return setting
