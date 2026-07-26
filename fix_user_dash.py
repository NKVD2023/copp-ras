with open("app/templates/user_dashboard.html", "r") as f:
    content = f.read()

# Replace Активные отчеты
old_active = '''<i class="bi bi-file-earmark-text"></i> Активные отчеты'''
new_active = '''<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"/></svg>
                    Активные отчеты'''
content = content.replace(old_active, new_active)

# Replace Просроченные
old_overdue_btn = '''<button class="admin-nav-link d-flex align-items-center gap-2 text-danger" data-bs-toggle="tab" data-bs-target="#overdueTab" type="button">
                    <i class="bi bi-exclamation-triangle"></i> Просроченные'''
new_overdue_btn = '''<button class="admin-nav-link d-flex align-items-center gap-2" data-bs-toggle="tab" data-bs-target="#overdueTab" type="button">
                    <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.146.146 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.163.163 0 0 1-.054.06.116.116 0 0 1-.066.017H1.146a.115.115 0 0 1-.066-.017.163.163 0 0 1-.054-.06.176.176 0 0 1 .002-.183L7.884 2.073a.147.147 0 0 1 .054-.057zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566z"/><path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/></svg>
                    Просроченные'''
content = content.replace(old_overdue_btn, new_overdue_btn)

# Replace Архив (Сданные)
old_archive = '''<i class="bi bi-archive"></i> Архив (Сданные)'''
new_archive = '''<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><path d="M0 2a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1v7.5a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 1 12.5V5a1 1 0 0 1-1-1V2zm2 3v7.5A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5V5H2zm13-3H1v2h14V2zM5 7.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5z"/></svg>
                    Архив (Сданные)'''
content = content.replace(old_archive, new_archive)

# Replace Файлы
old_files = '''<i class="bi bi-paperclip"></i> Файлы'''
new_files = '''<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><path d="M4.5 3a2.5 2.5 0 0 1 5 0v9a1.5 1.5 0 0 1-3 0V5a.5.5 0 0 1 1 0v7a.5.5 0 0 0 1 0V3a1.5 1.5 0 1 0-3 0v9a2.5 2.5 0 0 0 5 0V5a.5.5 0 0 1 1 0v7a3.5 3.5 0 1 1-7 0V3z"/></svg>
                    Файлы'''
content = content.replace(old_files, new_files)

# Replace Личный кабинет
old_profile = '''<i class="bi bi-person-circle"></i> Личный кабинет'''
new_profile = '''<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4Zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10Z"/></svg>
                    Личный кабинет'''
content = content.replace(old_profile, new_profile)

with open("app/templates/user_dashboard.html", "w") as f:
    f.write(content)
print("Updated successfully")
