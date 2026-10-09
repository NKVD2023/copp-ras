"""
app/admin/routes_logs.py — Маршруты для модуля «Журнал действий» (аудит).
Поддерживает ленивую загрузку (Lazy Loading), серверную пагинацию,
фильтрацию и серверный экспорт в CSV (UTF-8 с BOM).
"""
import io
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.admin import admin_bp
from app.auth.decorators import roles_required
from app.models import ActionLog, User
from app.extensions import db


def to_msk(dt):
    """Сдвигает datetime из UTC в московское время (UTC+3)."""
    if dt:
        return dt + timedelta(hours=3)
    return dt


@admin_bp.route('/logs/api', methods=['GET'])
@login_required
@roles_required('admin')
def get_logs_api():
    """
    Легковесный API-эндпоинт для ленивой загрузки логов.
    Возвращает страницу записей журнала действий с фильтрацией и пагинацией.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    if per_page not in [25, 50, 100, 200]:
        per_page = 50
    if page < 1:
        page = 1

    search = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    action_filter = request.args.get('action', '').strip()
    date_range = request.args.get('date_range', '').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    # Базовый запрос с внешним соединением с таблицей пользователей
    query = ActionLog.query.outerjoin(User, ActionLog.user_id == User.id)

    # 1. Текстовый поиск (по действию, деталям, IP, логину, описанию организации)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ActionLog.action.ilike(search_pattern),
                ActionLog.details.ilike(search_pattern),
                ActionLog.ip_address.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.description.ilike(search_pattern)
            )
        )

    # 2. Фильтр по роли
    if role:
        if role == 'system':
            query = query.filter(ActionLog.user_id.is_(None))
        else:
            query = query.filter(User.role == role)

    # 3. Фильтр по типу действия
    if action_filter:
        query = query.filter(ActionLog.action == action_filter)

    # 4. Фильтр по дате (с переводом МСК в UTC для запроса к БД)
    now_msk = datetime.utcnow() + timedelta(hours=3)
    if date_range == 'today':
        start_msk = datetime(now_msk.year, now_msk.month, now_msk.day)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_range == 'week':
        start_msk = (now_msk - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_range == 'month':
        start_msk = (now_msk - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_from_str or date_to_str:
        if date_from_str:
            try:
                df = datetime.strptime(date_from_str, '%Y-%m-%d')
                query = query.filter(ActionLog.timestamp >= df - timedelta(hours=3))
            except ValueError:
                pass
        if date_to_str:
            try:
                dt = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(ActionLog.timestamp < dt - timedelta(hours=3))
            except ValueError:
                pass

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    if page > total_pages and total_count > 0:
        page = total_pages

    # Сортировка: самые свежие события сверху
    logs = query.order_by(ActionLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for log in logs:
        msk_dt = to_msk(log.timestamp)
        items.append({
            'id': log.id,
            'timestamp_formatted': msk_dt.strftime('%d.%m.%Y %H:%M') if msk_dt else '',
            'timestamp_iso': msk_dt.strftime('%Y-%m-%d %H:%M:%S') if msk_dt else '',
            'user': {
                'id': log.user.id if log.user else None,
                'username': log.user.username if log.user else 'Система',
                'description': log.user.description if (log.user and log.user.description and log.user.description != 'None') else '',
                'role': log.user.role if log.user else 'system'
            },
            'action': log.action or '',
            'details': log.details or '',
            'ip_address': log.ip_address or ''
        })

    # Список уникальных действий для селектора фильтров
    actions_query = db.session.query(ActionLog.action).distinct().all()
    unique_actions = sorted([a[0] for a in actions_query if a[0]])

    return jsonify({
        'status': 'success',
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_count,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        },
        'unique_actions': unique_actions
    })


@admin_bp.route('/logs/export', methods=['GET'])
@login_required
@roles_required('admin')
def export_logs_xlsx():
    """
    Серверный экспорт журнала в формат Microsoft Excel (.xlsx)
    с учетом текущих фильтров в корпоративных цветах ЦОПП.
    """
    search = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    action_filter = request.args.get('action', '').strip()
    date_range = request.args.get('date_range', '').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    query = ActionLog.query.outerjoin(User, ActionLog.user_id == User.id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ActionLog.action.ilike(search_pattern),
                ActionLog.details.ilike(search_pattern),
                ActionLog.ip_address.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.description.ilike(search_pattern)
            )
        )

    if role:
        if role == 'system':
            query = query.filter(ActionLog.user_id.is_(None))
        else:
            query = query.filter(User.role == role)

    if action_filter:
        query = query.filter(ActionLog.action == action_filter)

    now_msk = datetime.utcnow() + timedelta(hours=3)
    if date_range == 'today':
        start_msk = datetime(now_msk.year, now_msk.month, now_msk.day)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_range == 'week':
        start_msk = (now_msk - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_range == 'month':
        start_msk = (now_msk - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ActionLog.timestamp >= start_msk - timedelta(hours=3))
    elif date_from_str or date_to_str:
        if date_from_str:
            try:
                df = datetime.strptime(date_from_str, '%Y-%m-%d')
                query = query.filter(ActionLog.timestamp >= df - timedelta(hours=3))
            except ValueError:
                pass
        if date_to_str:
            try:
                dt = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(ActionLog.timestamp < dt - timedelta(hours=3))
            except ValueError:
                pass

    logs = query.order_by(ActionLog.timestamp.desc()).all()

    # Создаем Excel-книгу через openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Журнал действий"

    headers = [
        "Дата и время (МСК)",
        "Пользователь",
        "Роль",
        "Организация / Описание",
        "Действие",
        "Подробности",
        "IP-адрес"
    ]
    ws.append(headers)

    # Корпоративный стиль ЦОПП: темно-синяя шапка (#00334E) с белым текстом
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="00334E", end_color="00334E", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    ws.row_dimensions[1].height = 28
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    role_names = {
        'admin': 'Администратор',
        'manager': 'Редактор',
        'user': 'Пользователь',
        'system': 'Система'
    }

    # Заполнение строк данными
    for row_idx, log in enumerate(logs, start=2):
        msk_dt = to_msk(log.timestamp)
        dt_str = msk_dt.strftime('%d.%m.%Y %H:%M') if msk_dt else ''
        username = log.user.username if log.user else 'Система'
        role_label = role_names.get(log.user.role, log.user.role) if log.user else 'Система'
        desc = log.user.description if (log.user and log.user.description and log.user.description != 'None') else ''
        details_clean = (log.details or '').replace('\r\n', ' ').replace('\n', ' ')

        row_values = [
            dt_str,
            username,
            role_label,
            desc,
            log.action or '',
            details_clean,
            log.ip_address or ''
        ]
        ws.append(row_values)

        ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=row_idx, column=2).alignment = Alignment(vertical="center")
        ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=row_idx, column=4).alignment = Alignment(vertical="center")
        ws.cell(row=row_idx, column=5).alignment = Alignment(vertical="center")
        ws.cell(row=row_idx, column=6).alignment = Alignment(vertical="center")
        ws.cell(row=row_idx, column=7).alignment = Alignment(horizontal="center", vertical="center")

        for col_idx in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col_idx).border = thin_border

    # Настройка ширины столбцов под содержимое
    column_widths = {
        'A': 20,
        'B': 22,
        'C': 18,
        'D': 35,
        'E': 26,
        'F': 55,
        'G': 18
    }
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    today_str = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y-%m-%d')
    filename = f"copp_logs_{today_str}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
