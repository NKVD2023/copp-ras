import os
import re

def resolve_db_tabs():
    filepath = r'app\templates\admin_tabs\db_tabs.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Conflict 1: lines 148-176
    content = re.sub(r'<<<<<<< HEAD.*?=======.*?\n>>>>>>> [a-f0-9]+\n', '', content, flags=re.DOTALL)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def resolve_logs_tabs():
    filepath = r'app\templates\admin_tabs\logs_tabs.html'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Conflict 1: lines 3-25
    content = re.sub(r'<<<<<<< HEAD.*?=======\n', '', content, flags=re.DOTALL)
    content = re.sub(r'>>>>>>> [a-f0-9]+\n', '', content)
    
    # Need to add csrf_token to the form at the bottom
    content = content.replace(
        '<form action="{{ url_for(\'admin.clear_logs\') }}" method="POST" onsubmit="return confirm(\'Вы уверены, что хотите удалить все логи? Это действие необратимо.\');" class="m-0">',
        '<form action="{{ url_for(\'admin.clear_logs\') }}" method="POST" onsubmit="return confirm(\'Вы уверены, что хотите удалить все логи? Это действие необратимо.\');" class="m-0">\n            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>'
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

resolve_db_tabs()
resolve_logs_tabs()
print("Done")
