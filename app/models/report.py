"""app/models/report.py — Шаблоны, сданные отчёты и черновики."""
from app.extensions import db
from sqlalchemy import JSON
from datetime import datetime
from app.models.files import report_attachments

class ReportTemplate(db.Model):
    """Шаблон отчёта. Структура полей хранится в schema (JSON)."""
    __tablename__ = 'report_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    short_name = db.Column(db.String(64))
    period = db.Column(db.String(128))
    period_data = db.Column(JSON, nullable=True)
    deadline = db.Column(db.Date)
    is_published = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    is_template = db.Column(db.Boolean, default=False)
    schema = db.Column(JSON)
    attachments = db.relationship(
        'UploadedFile', secondary=report_attachments,
        backref=db.backref('reports', lazy='dynamic')
    )

class ReportSubmission(db.Model):
    """Заполненный отчёт пользователя."""
    __tablename__ = 'report_submissions'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data = db.Column(JSON)
    is_revision = db.Column(db.Boolean, default=False)
    revision_comment = db.Column(db.Text, nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)
    returned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    template = db.relationship('ReportTemplate', backref='submissions')
    user = db.relationship('User', foreign_keys=[user_id], backref='submissions')
    returned_by = db.relationship('User', foreign_keys=[returned_by_id])

class ReportDraft(db.Model):
    """Облачный черновик отчёта. Один на пару (user, template)."""
    __tablename__ = 'report_drafts'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(JSON)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('template_id', 'user_id', name='uq_draft_template_user'),)
    template = db.relationship('ReportTemplate', backref='drafts')
    user = db.relationship('User', backref='drafts')
