"""
Модуль аутентификации (Auth).
Отвечает за вход пользователей в систему (логин) и выход (логаут).
В зависимости от роли пользователя (admin/viewer или user) происходит 
перенаправление на разные стартовые страницы.
"""
from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, current_user
from app.models import User
from app.utils import log_action
from app import limiter

# Регистрация Blueprint для маршрутов авторизации
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """
    Обработчик страницы авторизации.
    GET: Отображает форму входа (login.html).
    POST: Проверяет логин/пароль и осуществляет вход в систему.
    """
    # Если пользователь уже вошел, отправляем его на дашборд
    if current_user.is_authenticated:
        return redirect(url_for('reports.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Проверка существования пользователя и корректности пароля
        if user is None or not user.check_password(password):
            flash('Неверное имя пользователя или пароль')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        log_action('Вход в систему', f'Успешный вход пользователя {user.username}')
        
        # Разделение прав доступа при первом входе:
        # Админы и наблюдатели попадают в админ-панель
        if user.role in ['admin', 'viewer']:
            return redirect(url_for('admin.dashboard'))
            
        # Обычные учреждения попадают на свою панель отчетов
        return redirect(url_for('reports.dashboard'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """
    Выход из системы.
    Записывает действие в лог, очищает сессию Flask-Login и возвращает на окно входа.
    """
    log_action('Выход из системы')
    logout_user()
    return redirect(url_for('auth.login'))