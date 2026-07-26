import os
import glob

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old_str, new_str in replacements:
        new_content = new_content.replace(old_str, new_str)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

def main():
    base_dir = '/home/copp-admin/copp-ras'
    
    replacements_py = [
        ("'manager'", "'manager'"),
        ('"manager"', '"manager"'),
        ("role == 'manager'", "role == 'manager'"),
        ("role in ['admin', 'manager']", "role in ['admin', 'manager']"),
        ("roles_required('admin', 'manager')", "roles_required('admin', 'manager')"),
        ("Руководитель отдела", "Руководитель отдела")
    ]
    
    replacements_html = [
        ("'manager'", "'manager'"),
        ('"manager"', '"manager"'),
        ("viewer.css", "manager.css"),
        ("viewerTabs", "managerTabs"),
        ("Руководитель отдела", "Руководитель отдела"),
        ("Руководитель отдела (Только просмотр)", "Руководитель отдела (Только просмотр)")
    ]

    for root, _, files in os.walk(base_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                replace_in_file(os.path.join(root, file), replacements_py)
            elif file.endswith('.html'):
                replace_in_file(os.path.join(root, file), replacements_html)
                
    # Rename viewer.css to manager.css
    css_old = os.path.join(base_dir, 'app', 'static', 'css', 'viewer.css')
    css_new = os.path.join(base_dir, 'app', 'static', 'css', 'manager.css')
    if os.path.exists(css_old):
        os.rename(css_old, css_new)
        print("Renamed viewer.css to manager.css")
        
    # Rename viewer_dashboard.html to manager_dashboard.html
    html_old = os.path.join(base_dir, 'app', 'templates', 'viewer_dashboard.html')
    html_new = os.path.join(base_dir, 'app', 'templates', 'manager_dashboard.html')
    if os.path.exists(html_old):
        os.rename(html_old, html_new)
        print("Renamed viewer_dashboard.html to manager_dashboard.html")

if __name__ == '__main__':
    main()
