import os
import re

template_dir = r"c:\Users\admin-copp\Documents\GitHub\copp-ras\app\templates"

form_regex = re.compile(r'(<form[^>]*>)', re.IGNORECASE)
csrf_input = r'\1\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>'

fetch_headers_regex = re.compile(r"(headers\s*:\s*\{)([^}]*)(\})", re.IGNORECASE)
def inject_header(match):
    prefix = match.group(1)
    content = match.group(2)
    suffix = match.group(3)
    if 'X-CSRFToken' not in content:
        if content.strip():
            return f"{prefix}{content}, 'X-CSRFToken': '{{{{ csrf_token() }}}}'{suffix}"
        else:
            return f"{prefix}'X-CSRFToken': '{{{{ csrf_token() }}}}'{suffix}"
    return match.group(0)

fetch_no_headers_regex = re.compile(r"(fetch\([^,]+,\s*\{)(?!\s*headers)", re.IGNORECASE)
def inject_new_headers(match):
    return f"{match.group(1)} headers: {{ 'X-CSRFToken': '{{{{ csrf_token() }}}}' }},"

for root, _, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            if '<form' in content.lower():
                if 'csrf_token' not in content:
                    content = form_regex.sub(csrf_input, content)
            
            if 'fetch(' in content:
                content = fetch_headers_regex.sub(inject_header, content)
                content = fetch_no_headers_regex.sub(inject_new_headers, content)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")
