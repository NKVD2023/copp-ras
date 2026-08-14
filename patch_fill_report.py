import re

with open('app/templates/fill_report.html', 'r') as f:
    content = f.read()

# Replace macro signature
content = content.replace(
    "{% macro render_input(field, submission, is_locked) %}",
    "{% macro render_input(field, submission, is_locked, group_index=none) %}"
)

# Fix raw_val to use group_index if provided
old_raw_val_multiple = "{% set raw_val = submission.data.get(field.name) if submission else None %}"
new_raw_val_multiple = """{% set raw_val = submission.data.get(field.name) if submission else None %}
                            {% if group_index is not none and raw_val is iterable and raw_val is not string %}
                                {% set raw_val = raw_val[group_index] if group_index < raw_val|length else '' %}
                            {% endif %}"""
content = content.replace(old_raw_val_multiple, new_raw_val_multiple)

old_single_input = """                            <div class="input-wrapper">
                                {% if field.type == 'text' or field.type == 'Текстовое' %}
                                    <textarea class="form-control" name="{{ field.name }}" rows="3" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>{{ submission.data.get(field.name, '') if submission else '' }}</textarea>
                                {% elif field.type == 'select' %}
                                    <select class="form-select" name="{{ field.name }}" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>
                                        <option value="">-- Выберите значение --</option>
                                        {% for opt in field.options %}
                                        <option value="{{ opt }}" {% if submission and submission.data.get(field.name) == opt %}selected{% endif %}>{{ opt }}</option>
                                        {% endfor %}
                                    </select>
                                {% else %}
                                    <input type="number" class="form-control" name="{{ field.name }}"
                                        value="{{ submission.data.get(field.name, '') if submission else '' }}" min="0" step="any" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>
                                {% endif %}
                            </div>"""

new_single_input = """                            <div class="input-wrapper">
                                {% set single_val = submission.data.get(field.name, '') if submission else '' %}
                                {% if group_index is not none and single_val is iterable and single_val is not string %}
                                    {% set single_val = single_val[group_index] if group_index < single_val|length else '' %}
                                {% endif %}
                                {% if field.type == 'text' or field.type == 'Текстовое' %}
                                    <textarea class="form-control" name="{{ field.name }}" rows="3" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>{{ single_val }}</textarea>
                                {% elif field.type == 'select' %}
                                    <select class="form-select" name="{{ field.name }}" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>
                                        <option value="">-- Выберите значение --</option>
                                        {% for opt in field.options %}
                                        <option value="{{ opt }}" {% if single_val == opt %}selected{% endif %}>{{ opt }}</option>
                                        {% endfor %}
                                    </select>
                                {% else %}
                                    <input type="number" class="form-control" name="{{ field.name }}"
                                        value="{{ single_val }}" min="0" step="any" {% if field.required %}required{% endif %} {% if is_locked %}disabled{% endif %}>
                                {% endif %}
                            </div>"""
content = content.replace(old_single_input, new_single_input)

# Replace render_field_node signature
content = content.replace(
    "{% macro render_field_node(node, submission, is_locked) %}",
    "{% macro render_field_node(node, submission, is_locked, group_index=none) %}"
)
content = content.replace(
    "{{ render_input(field, submission, effective_locked) }}",
    "{{ render_input(field, submission, effective_locked, group_index) }}"
)
content = content.replace(
    "{{ render_field_node(child, submission, is_locked) }}",
    "{{ render_field_node(child, submission, is_locked, group_index) }}"
)

with open('app/templates/fill_report.html', 'w') as f:
    f.write(content)
