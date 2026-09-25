"""
Модуль аутентификации (Auth).
Отвечает за вход пользователей в систему (логин) и выход (логаут).
В зависимости от роли пользователя (admin/viewer или user) происходит 
перенаправление на разные стартовые страницы.
"""
from flask import Blueprint, render_template, redirect, request, url_for, flash, session
from flask_login import login_user, logout_user, current_user
import time
from app.models import User
from app.utils import log_action
from app.extensions import limiter

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
    from app.services.maintenance import get_maintenance_status
    m_status = get_maintenance_status()

    # Если пользователь уже вошел:
    if current_user.is_authenticated:
        # Если активен режим техработ и текущий пользователь не админ —
        # сбрасываем сессию, чтобы дать возможность войти как администратор
        if m_status.get('in_maintenance') and current_user.role != 'admin':
            logout_user()
            session.clear()
        elif current_user.role in ['admin', 'manager']:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('reports.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Проверка существования пользователя и корректности пароля
        if user is None or not user.check_password(password):
            flash('Неверное имя пользователя или пароль', 'danger')
            return redirect(url_for('auth.login'))
            
        session.permanent = True
        session['login_time'] = time.time()
        login_user(user)
        log_action('Вход в систему', f'Успешный вход пользователя {user.username}')
        
        # Разделение прав доступа при первом входе:
        # Админы и наблюдатели попадают в админ-панель
        if user.role in ['admin', 'manager']:
            return redirect(url_for('admin.dashboard'))
            
        # Обычные учреждения попадают на свою панель отчетов
        return redirect(url_for('reports.dashboard'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """
    Выход из системы.
    Записывает действие в лог, полностью очищает сессию и возвращает на окно входа.
    """
    log_action('Выход из системы')
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/test_expire')
def test_expire():
    """
    Тестовый маршрут для проверки суточного таймаута:
    Искусственно сдвигает login_time текущей сессии на 25 часов назад (на 90 000 сек).
    """
    session['login_time'] = time.time() - 90000
    return (
        '<div style="font-family: sans-serif; padding: 30px; text-align: center;">'
        '<h3 style="color: #00334e;">Время входа успешно сдвинуто на 25 часов назад!</h3>'
        '<p style="color: #64748b;">Сервер считает, что вы вошли вчера. '
        'Теперь при любом переходе по системе сработает суточный лимит.</p>'
        '<p><a href="/" style="display: inline-block; padding: 10px 20px; background: #00334e; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Перейти в систему (проверить разлогин)</a></p>'
        '</div>'
    )

from flask_login import login_required
from app.extensions import db

@auth_bp.route('/change_my_password', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def change_my_password():
    """Смена собственного пароля."""
    new_password = request.form.get('new_password')
    if new_password:
        current_user.set_password(new_password)
        db.session.commit()
        log_action('Смена пароля', f'Пользователь {current_user.username} сменил свой пароль')
    if current_user.role in ['admin', 'manager']:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('reports.dashboard'))
