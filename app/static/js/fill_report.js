/**
 * fill_report.js
 * Главный координатор страницы заполнения отчета.
 * Модули: wizard.js, autosave.js, previous_data.js, dynamic_fields.js
 */
(function () {
    'use strict';

    window.getFormDataObj = function(formElement) {
        const formData = new FormData(formElement);
        const dataObj = {};
        const multipleInputs = Array.from(formElement.querySelectorAll('[data-multiple="true"]'));
        const multipleNames = new Set(multipleInputs.map(el => el.name));

        for (const key of new Set(formData.keys())) {
            if (multipleNames.has(key)) {
                dataObj[key] = formData.getAll(key);
            } else {
                dataObj[key] = formData.get(key);
            }
        }
        return dataObj;
    };

    document.addEventListener('DOMContentLoaded', () => {
        const form   = document.getElementById('reportForm');
        const config = window.FILL_CONFIG || {};

        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el, { trigger: 'hover' });
        });

        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach((tab, index) => {
            tab.addEventListener('shown.bs.tab', () => {
                if (window.updateWizardButtons) window.updateWizardButtons(index);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
        if (window.updateWizardButtons) window.updateWizardButtons(0);

        if (!config.isLocked && !config.isPreview && config.draftKey) {
            const savedDraft = localStorage.getItem(config.draftKey);
            if (savedDraft) {
                try {
                    const data = JSON.parse(savedDraft);
                    let restored = false;
                    for (const [name, value] of Object.entries(data)) {
                        if (name === 'csrf_token') continue;
                        if (Array.isArray(value)) {
                            const wrapper = document.querySelector(`.dynamic-field-wrapper[data-name="${name}"]`);
                            if (wrapper) {
                                const items = wrapper.querySelectorAll('.dynamic-field-item');
                                if (items.length > 0) {
                                    const firstInput = items[0].querySelector('[name]');
                                    if (firstInput && (!firstInput.value || firstInput.value === '')) {
                                        firstInput.value = value[0] || '';
                                        restored = true;
                                        const addBtn = wrapper.querySelector('.btn-add-dynamic');
                                        if (addBtn && value.length > 1) {
                                            let type = 'number';
                                            if (firstInput.tagName === 'TEXTAREA') type = 'text';
                                            else if (firstInput.tagName === 'SELECT') type = 'select';
                                            for (let i = 1; i < value.length; i++) {
                                                if (window.addDynamicField) window.addDynamicField(addBtn, type, name, value[i]);
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            const field = form.elements[name];
                            if (field && (!field.value || field.value === '')) {
                                field.value = value;
                                restored = true;
                            }
                        }
                    }
                    if (restored) {
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-info py-2 small shadow-sm mb-4 border-info';
                        alertDiv.innerHTML = '<strong>Восстановлены несохраненные данные</strong> из локального черновика вашего браузера.';
                        form.parentNode.insertBefore(alertDiv, form);
                    }
                } catch (e) { console.error('Ошибка чтения черновика:', e); }
            }
            if (window.setupAutosave) window.setupAutosave(form);
        }

        if (typeof initRealTimeValidation === 'function') {
            window.runClientValidation = initRealTimeValidation(window.schemaTree, window.getFormDataObj, form);
        }
    });
})();
