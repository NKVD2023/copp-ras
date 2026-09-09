"""app/models/dictionaries.py — Справочники (источники для select-полей)."""
from app.extensions import db
from sqlalchemy import JSON
from datetime import datetime

class Dictionary(db.Model):
    __tablename__ = 'dictionaries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    items = db.Column(JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
