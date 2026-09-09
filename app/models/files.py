"""app/models/files.py — Загруженные файлы и таблица связи с шаблонами."""
from app.extensions import db
from datetime import datetime

report_attachments = db.Table(
    'report_attachments',
    db.Column('template_id', db.Integer, db.ForeignKey('report_templates.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('uploaded_files.id'), primary_key=True)
)

class UploadedFile(db.Model):
    """Файл (письмо, инструкция), прикреплённый к шаблону."""
    __tablename__ = 'uploaded_files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256))
    filepath = db.Column(db.String(256))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_size = db.Column(db.Integer)
    uploader = db.relationship('User', backref='uploaded_files')
