"""app/models/user.py — Модели пользователей."""
from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

user_template_access = db.Table(
    'user_template_access',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('template_id', db.Integer, db.ForeignKey('report_templates.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """Пользователь системы. Роли: admin, user, manager."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    description = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user')
    group = db.Column(db.String(50), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    assigned_templates = db.relationship(
        'ReportTemplate', secondary=user_template_access,
        backref=db.backref('assigned_users', lazy='dynamic')
    )
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
