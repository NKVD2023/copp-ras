from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, current_user
from app.models import User
from app.utils import log_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('reports.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Неверное имя пользователя или пароль')
            return redirect(url_for('auth.login'))
        login_user(user)
        log_action('Вход в систему', f'Успешный вход пользователя {user.username}')
        if user.role in ['admin', 'viewer']:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('reports.dashboard'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    log_action('Выход из системы')
    logout_user()
    return redirect(url_for('auth.login'))