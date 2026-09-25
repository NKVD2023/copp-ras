"""
app/admin/routes_announcements.py — Управление объявлениями для пользователей.
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import Announcement, Department, User
from app.extensions import db
from app.utils import log_action


@admin_bp.route('/announcements/create', methods=['POST'])
@login_required
def create_announcement():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    ann_type = request.form.get('type', 'info')
    is_active = True if request.form.get('is_active') == '1' else False
    target_type = request.form.get('target_type', 'all')

    target_departments = []
    target_groups = []

    if target_type == 'specific':
        raw_depts = request.form.getlist('target_departments')
        target_departments = [int(d) for d in raw_depts if d.isdigit()]

        raw_groups = request.form.getlist('target_groups')
        target_groups = [g.strip() for g in raw_groups if g.strip()]

    if not title or not content:
        flash('Заголовок и текст объявления обязательны для заполнения.', 'danger')
        return redirect(url_for('admin.dashboard', tab='announcementsTab'))

    # Для руководителя отдела фиксируем отдел
    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if dept:
            target_type = 'specific'
            target_departments = [dept.id]

    announcement = Announcement(
        title=title,
        content=content,
        type=ann_type,
        is_active=is_active,
        target_type=target_type,
        target_departments=target_departments,
        target_groups=target_groups,
        created_by_id=current_user.id
    )

    db.session.add(announcement)
    db.session.commit()

    log_action('Создание объявления', f'Создано объявление: "{title}" (активно: {is_active})')
    flash('Объявление успешно создано!', 'success')
    return redirect(url_for('admin.dashboard', tab='announcementsTab'))


@admin_bp.route('/announcements/<int:announcement_id>/edit', methods=['POST'])
@login_required
def edit_announcement(announcement_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    announcement = Announcement.query.get_or_404(announcement_id)

    if current_user.role == 'manager':
        from app.utils import get_manager_department
        dept = get_manager_department(current_user)
        if not dept or (announcement.created_by_id != current_user.id and (not announcement.target_departments or dept.id not in announcement.target_departments)):
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('admin.dashboard', tab='announcementsTab'))

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    ann_type = request.form.get('type', 'info')
    is_active = True if request.form.get('is_active') == '1' else False
    target_type = request.form.get('target_type', 'all')

    target_departments = []
    target_groups = []

    if target_type == 'specific':
        raw_depts = request.form.getlist('target_departments')
        target_departments = [int(d) for d in raw_depts if d.isdigit()]

        raw_groups = request.form.getlist('target_groups')
        target_groups = [g.strip() for g in raw_groups if g.strip()]

    if not title or not content:
        flash('Заголовок и текст объявления обязательны для заполнения.', 'danger')
        return redirect(url_for('admin.dashboard', tab='announcementsTab'))

    announcement.title = title
    announcement.content = content
    announcement.type = ann_type
    announcement.is_active = is_active
    announcement.target_type = target_type
    announcement.target_departments = target_departments
    announcement.target_groups = target_groups

    db.session.commit()

    log_action('Редактирование объявления', f'Обновлено объявление #{announcement.id}: "{title}"')
    flash('Объявление успешно обновлено!', 'success')
    return redirect(url_for('admin.dashboard', tab='announcementsTab'))


@admin_bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@login_required
def toggle_announcement(announcement_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    announcement = Announcement.query.get_or_404(announcement_id)

    announcement.is_active = not announcement.is_active
    db.session.commit()

    status_str = "запущено" if announcement.is_active else "остановлено"
    log_action('Переключение статуса объявления', f'Объявление #{announcement.id} {status_str}')

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'success',
            'is_active': announcement.is_active,
            'message': f'Объявление {status_str}'
        })

    flash(f'Объявление успешно {status_str}!', 'success')
    return redirect(url_for('admin.dashboard', tab='announcementsTab'))


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'status': 'error', 'message': 'Доступ ограничен'}), 403

    announcement = Announcement.query.get_or_404(announcement_id)

    title = announcement.title
    db.session.delete(announcement)
    db.session.commit()

    log_action('Удаление объявления', f'Удалено объявление: "{title}"')
    flash('Объявление удалено.', 'success')
    return redirect(url_for('admin.dashboard', tab='announcementsTab'))
