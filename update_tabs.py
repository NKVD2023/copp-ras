import re

filepath = '/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update total counts
old_counts = """        {% set total_unfilled = unfilled_templates|length %}
        {% set total_filled = filled_templates|length %}
        {% set total_assigned = total_unfilled + total_filled %}"""

new_counts = """        {% set total_unfilled = unfilled_templates|length %}
        {% set total_overdue = overdue_templates|length %}
        {% set total_filled = filled_templates|length %}
        {% set total_assigned = total_unfilled + total_overdue + total_filled %}"""

content = content.replace(old_counts, new_counts)

# Update nav tabs
old_nav = """        <ul class="nav nav-tabs mb-4" id="userTabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active d-flex align-items-center gap-2" data-bs-toggle="tab" data-bs-target="#unfilledTab" type="button">
                    Требуют заполнения 
                    {% if total_unfilled > 0 %}<span class="badge bg-danger rounded-pill">{{ total_unfilled }}</span>{% endif %}
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link d-flex align-items-center gap-2" data-bs-toggle="tab" data-bs-target="#filledTab" type="button">
                    Сданные (Архив)
                    {% if total_filled > 0 %}<span class="badge bg-success bg-opacity-75 rounded-pill">{{ total_filled }}</span>{% endif %}
                </button>
            </li>
        </ul>"""

new_nav = """        <ul class="nav nav-tabs mb-4" id="userTabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active d-flex align-items-center gap-2" data-bs-toggle="tab" data-bs-target="#unfilledTab" type="button">
                    Требуют заполнения 
                    {% if total_unfilled > 0 %}<span class="badge bg-primary rounded-pill">{{ total_unfilled }}</span>{% endif %}
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link d-flex align-items-center gap-2 text-danger" data-bs-toggle="tab" data-bs-target="#overdueTab" type="button">
                    Просроченные
                    {% if total_overdue > 0 %}<span class="badge bg-danger rounded-pill">{{ total_overdue }}</span>{% endif %}
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link d-flex align-items-center gap-2" data-bs-toggle="tab" data-bs-target="#filledTab" type="button">
                    Сданные (Архив)
                    {% if total_filled > 0 %}<span class="badge bg-success bg-opacity-75 rounded-pill">{{ total_filled }}</span>{% endif %}
                </button>
            </li>
        </ul>"""

content = content.replace(old_nav, new_nav)

# Extract the template block for unfilled items to reuse for overdue
template_block_regex = re.compile(r'{% for template in unfilled_templates %}.*?{% endfor %}', re.DOTALL)
match = template_block_regex.search(content)

if match:
    unfilled_loop = match.group(0)
    overdue_loop = unfilled_loop.replace('unfilled_templates', 'overdue_templates').replace('У вас нет активных отчетов, требующих заполнения.', 'Нет просроченных отчетов.')
    
    # Insert new tab pane
    new_pane = f"""
            <div class="tab-pane fade" id="overdueTab" role="tabpanel">
                <div class="row g-4" id="overdueContainer">
                    {overdue_loop}
                </div>
            </div>
"""
    # Find the end of unfilledTab pane
    unfilled_end = '            <div class="tab-pane fade" id="filledTab" role="tabpanel">'
    content = content.replace(unfilled_end, new_pane + '\n' + unfilled_end)

# Also update the JS processing function
old_js = """                    // Process unfilled items
                    processContainer('unfilledContainer', query, sortVal);
                    // Process filled items
                    processContainer('filledContainer', query, sortVal);"""

new_js = """                    // Process unfilled items
                    processContainer('unfilledContainer', query, sortVal);
                    // Process overdue items
                    processContainer('overdueContainer', query, sortVal);
                    // Process filled items
                    processContainer('filledContainer', query, sortVal);"""
content = content.replace(old_js, new_js)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated HTML.")
