import re

with open("app/templates/user_dashboard.html", "r") as f:
    content = f.read()

# Remove the badges using regex
content = re.sub(r'\{% if total_unfilled > 0 %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)
content = re.sub(r'\{% if total_overdue > 0 %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)
content = re.sub(r'\{% if total_filled > 0 %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)
content = re.sub(r'\{% if attached_files\|length > 0 %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)

with open("app/templates/user_dashboard.html", "w") as f:
    f.write(content)
print("Badges removed.")
