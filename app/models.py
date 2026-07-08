from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import JSON
from datetime import date, datetime

user_template_access = db.Table('user_template_access',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('template_id', db.Integer, db.ForeignKey('report_templates.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    description = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user')
    assigned_templates = db.relationship('ReportTemplate', secondary=user_template_access, backref=db.backref('assigned_users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ReportTemplate(db.Model):
    __tablename__ = 'report_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    short_name = db.Column(db.String(64))
    period = db.Column(db.String(128))
    deadline = db.Column(db.Date)
    is_published = db.Column(db.Boolean, default=False)
    schema = db.Column(JSON)

class ReportSubmission(db.Model):
    __tablename__ = 'report_submissions'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data = db.Column(JSON)
    template = db.relationship('ReportTemplate', backref='submissions')
    user = db.relationship('User', backref='submissions')

class ActionLog(db.Model):
    __tablename__ = 'action_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(128))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='action_logs')

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))