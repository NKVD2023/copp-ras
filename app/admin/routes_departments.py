"""
app/admin/routes_departments.py
CRUD управление отделами. Доступно только администратору (admin).
Менеджер (manager) своим отделом управлять не может — только видит его данные.
"""
import json
from flask import request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.extensions import db
from app.models import Department, User, ReportTemplate
from app.utils import log_action
from app.auth.decorators import roles_required


# ==========================================
# СОЗДАНИЕ ОТДЕЛА
# ==========================================
@admin_bp.route('/department/create', methods=['POST'])
@login_required
@roles_required('admin')
def create_department():
    """Создать новый отдел."""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Название отдела не может быть пустым.')
        return redirect(url_for('admin.dashboard') + '#departmentsTab')

    if Department.query.filter_by(name=name).first():
        flash(f'Отдел «{name}» уже существует.')
        return redirect(url_for('admin.dashboard') + '#departmentsTab')

    manager_ids = request.form.getlist('manager_ids')

    dept = Department(name=name)
    dept.manager_ids_list = manager_ids
    db.session.add(dept)
    db.session.flush()  # получаем dept.id до commit

    # Назначаем целыми группами
    groups = request.form.getlist('groups')
    if groups:
        group_users = User.query.filter(User.group.in_(groups)).all()
        for u in group_users:
            u.department_id = dept.id

    # Назначаем выбранных индивидуальных пользователей в отдел
    user_ids = request.form.getlist('user_ids')
    for uid in user_ids:
        u = User.query.get(int(uid))
        if u:
            u.department_id = dept.id

    # Назначаем шаблоны отчетов
    template_ids = request.form.getlist('template_ids')
    for tid in template_ids:
        t = ReportTemplate.query.get(int(tid))
        if t:
            dept.templates.append(t)

    # Назначаем файлы
    from app.models import UploadedFile, Dictionary
    file_ids = request.form.getlist('file_ids')
    for fid in file_ids:
        f = UploadedFile.query.get(int(fid))
        if f:
            f.department_id = dept.id
            
    # Назначаем справочники
    dict_ids = request.form.getlist('dictionary_ids')
    for did in dict_ids:
        d = Dictionary.query.get(int(did))
        if d:
            d.department_id = dept.id

    db.session.commit()
    log_action('Создание отдела', f'Создан отдел: {name}')
    return redirect(url_for('admin.dashboard') + '#departmentsTab')


# ==========================================
# РЕДАКТИРОВАНИЕ ОТДЕЛА
# ==========================================
@admin_bp.route('/department/<int:dept_id>/edit', methods=['POST'])
@login_required
@roles_required('admin')
def edit_department(dept_id):
    """Редактировать отдел: название, руководитель, пользователи, шаблоны."""
    dept = Department.query.get_or_404(dept_id)

    name = request.form.get('name', '').strip()
    if name and name != dept.name:
        existing = Department.query.filter_by(name=name).first()
        if existing and existing.id != dept.id:
            flash(f'Отдел «{name}» уже существует.')
            return redirect(url_for('admin.dashboard') + '#departmentsTab')
        dept.name = name

    manager_ids = request.form.getlist('manager_ids')
    dept.manager_ids_list = manager_ids

    # Пересобираем список пользователей:
    # 1) Снимаем department_id у всех текущих участников
    for u in dept.members.all():
        u.department_id = None

    # 2) Назначаем department_id новым участникам
    groups = request.form.getlist('groups')
    if groups:
        group_users = User.query.filter(User.group.in_(groups)).all()
        for u in group_users:
            u.department_id = dept.id
            
    user_ids = request.form.getlist('user_ids')
    for uid in user_ids:
        u = User.query.get(int(uid))
        if u:
            u.department_id = dept.id

    # Пересобираем шаблоны
    dept.templates = []
    template_ids = request.form.getlist('template_ids')
    for tid in template_ids:
        t = ReportTemplate.query.get(int(tid))
        if t and t not in dept.templates:
            dept.templates.append(t)

    from app.models import UploadedFile, Dictionary
    # Пересобираем файлы
    for f in UploadedFile.query.filter_by(department_id=dept.id).all():
        f.department_id = None
    file_ids = request.form.getlist('file_ids')
    for fid in file_ids:
        f = UploadedFile.query.get(int(fid))
        if f:
            f.department_id = dept.id
            
    # Пересобираем справочники
    for d in Dictionary.query.filter_by(department_id=dept.id).all():
        d.department_id = None
    dict_ids = request.form.getlist('dictionary_ids')
    for did in dict_ids:
        d = Dictionary.query.get(int(did))
        if d:
            d.department_id = dept.id

    db.session.commit()
    log_action('Редактирование отдела', f'Обновлён отдел: {dept.name}')
    return redirect(url_for('admin.dashboard') + '#departmentsTab')


# ==========================================
# УДАЛЕНИЕ ОТДЕЛА
# ==========================================
@admin_bp.route('/department/<int:dept_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_department(dept_id):
    """Удалить отдел. Пользователи отдела остаются, просто отвязываются."""
    dept = Department.query.get_or_404(dept_id)

    # Открепляем пользователей (не удаляем их!)
    for u in dept.members.all():
        u.department_id = None

    from app.models import UploadedFile, Dictionary
    # Открепляем файлы и справочники
    for f in UploadedFile.query.filter_by(department_id=dept.id).all():
        f.department_id = None
    for d in Dictionary.query.filter_by(department_id=dept.id).all():
        d.department_id = None

    dept_name = dept.name
    db.session.delete(dept)
    db.session.commit()
    log_action('Удаление отдела', f'Удалён отдел: {dept_name}')
    return redirect(url_for('admin.dashboard') + '#departmentsTab')

