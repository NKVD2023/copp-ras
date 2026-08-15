import re

with open('app/templates/report_data_view.html', 'r') as f:
    content = f.read()

# We need to replace the `{% for sub in submissions %}` block
# Up to `{% endfor %} <!-- end for sub -->` (or just endfor)

old_block = """                            {% for sub in submissions %}
                            <tr>
                                <td class="p-3 fw-bold sticky-col">{{ sub.user.description }}</td>
                                {% for field in sheet.leaf_fields %}
                                {% set is_active = field.get('is_active', True) %}
                                {% set val = sub.data.get(field.name, '') %}
                                {% if not is_active and (val is none or val == '' or val == []) %}
                                    {% set val = 'Сбор завершен' %}
                                {% endif %}
                                <td class="p-0 align-top text-center {% if not is_active %}bg-light text-muted{% else %}text-dark{% endif %}" title="{% if is_active %}Кликните для редактирования{% else %}Сбор данных завершен{% endif %}">
                                    {% if val is iterable and val is not string %}
                                        {% for v in val %}
                                        <div class="p-3 {% if not loop.last %}border-bottom{% endif %}" 
                                             contenteditable="{% if is_active %}true{% else %}false{% endif %}" 
                                             data-user-id="{{ sub.user.id }}"
                                             data-field-name="{{ field.name }}"
                                             data-is-multiple="true"
                                             data-index="{{ loop.index0 }}">{{ v }}</div>
                                        {% endfor %}
                                        {% if val|length == 0 %}
                                        <div class="p-3" contenteditable="{% if is_active %}true{% else %}false{% endif %}" data-user-id="{{ sub.user.id }}" data-field-name="{{ field.name }}" data-is-multiple="true" data-index="0">{{ val if not is_active else '' }}</div>
                                        {% endif %}
                                    {% else %}
                                        <div class="p-3" 
                                             contenteditable="{% if is_active %}true{% else %}false{% endif %}" 
                                             data-user-id="{{ sub.user.id }}"
                                             data-field-name="{{ field.name }}"
                                             data-is-multiple="false">{{ val }}</div>
                                    {% endif %}
                                </td>
                                {% endfor %}
                            </tr>
                            {% endfor %}"""

new_block = """                            {% for sub in submissions %}
                                {% set ns = namespace(max_len=1) %}
                                {% for field in sheet.leaf_fields %}
                                    {% set val = sub.data.get(field.name) %}
                                    {% if val is iterable and val is not string %}
                                        {% if val|length > ns.max_len %}{% set ns.max_len = val|length %}{% endif %}
                                    {% endif %}
                                {% endfor %}

                                {% for row_idx in range(ns.max_len) %}
                                <tr>
                                    {% if row_idx == 0 %}
                                    <td class="p-3 fw-bold sticky-col" rowspan="{{ ns.max_len }}">{{ sub.user.description }}</td>
                                    {% endif %}
                                    {% for field in sheet.leaf_fields %}
                                        {% set is_active = field.get('is_active', True) %}
                                        {% set val = sub.data.get(field.name, '') %}
                                        {% if not is_active and (val is none or val == '' or val == []) %}
                                            {% set val = 'Сбор завершен' %}
                                        {% endif %}
                                        
                                        {% if val is iterable and val is not string %}
                                            <td class="p-0 align-middle text-center {% if not is_active %}bg-light text-muted{% else %}text-dark{% endif %}" title="{% if is_active %}Кликните для редактирования{% else %}Сбор данных завершен{% endif %}">
                                                {% set v = val[row_idx] if row_idx < val|length else '' %}
                                                <div class="p-3" 
                                                     contenteditable="{% if is_active %}true{% else %}false{% endif %}" 
                                                     data-user-id="{{ sub.user.id }}"
                                                     data-field-name="{{ field.name }}"
                                                     data-is-multiple="true"
                                                     data-index="{{ row_idx }}">{{ v }}</div>
                                            </td>
                                        {% else %}
                                            {% if row_idx == 0 %}
                                            <td class="p-0 align-middle text-center {% if not is_active %}bg-light text-muted{% else %}text-dark{% endif %}" rowspan="{{ ns.max_len }}" title="{% if is_active %}Кликните для редактирования{% else %}Сбор данных завершен{% endif %}">
                                                <div class="p-3" 
                                                     contenteditable="{% if is_active %}true{% else %}false{% endif %}" 
                                                     data-user-id="{{ sub.user.id }}"
                                                     data-field-name="{{ field.name }}"
                                                     data-is-multiple="false">{{ val }}</div>
                                            </td>
                                            {% endif %}
                                        {% endif %}
                                    {% endfor %}
                                </tr>
                                {% endfor %}
                            {% endfor %}"""

content = content.replace(old_block, new_block)
with open('app/templates/report_data_view.html', 'w') as f:
    f.write(content)
