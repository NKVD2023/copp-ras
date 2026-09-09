/**
 * previous_data.js
 * Загрузка данных из предыдущих отчетов
 */
(function () {
    'use strict';

    window.loadPreviousData = function () {
        const btn = document.getElementById('btn-no-changes');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Загрузка...';

        fetch(window.FILL_CONFIG.prevDataUrl.replace('/previous_data', '/past_submissions'))
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                btn.innerHTML = originalText;

                if (data.status !== 'success') {
                    return coppAlert('Ошибка при получении списка: ' + data.message, 'error');
                }

                const pastList = data.data;
                if (!pastList || pastList.length === 0) {
                    return coppAlert('У вас нет заполненных отчетов за прошлые периоды для данного шаблона.', 'info');
                }

                const latestReport = pastList[0];

                Swal.fire({
                    title: 'Подтверждение',
                    html: `Данные будут скопированы из вашего последнего отчета:<br><b class="mt-2 d-inline-block text-primary">${latestReport.label}</b><br><br>Это действие перезапишет все текущие заполненные поля.`,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#003366',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Да, продолжить',
                    cancelButtonText: 'Отмена',
                }).then((result) => {
                    if (result.isConfirmed) {
                        fetchAndApplyPreviousData(latestReport.submission_id);
                    }
                });
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = originalText;
                coppAlert('Ошибка сети: ' + err, 'error');
            });
    };

    function fetchAndApplyPreviousData(submissionId) {
        const btn = document.getElementById('btn-no-changes');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Применение...';

        const url = window.FILL_CONFIG.prevDataUrl + '?submission_id=' + submissionId;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                btn.innerHTML = originalText;
                if (data.status === 'success') {
                    const form = document.getElementById('reportForm');
                    for (const [name, value] of Object.entries(data.data)) {
                        if (Array.isArray(value)) {
                            const wrapper = document.querySelector(`.dynamic-field-wrapper[data-name="${name}"]`);
                            if (wrapper) {
                                const items = wrapper.querySelectorAll('.dynamic-field-item');
                                if (items.length > 0) {
                                    const firstInput = items[0].querySelector('[name]');
                                    if (firstInput) {
                                        firstInput.value = value[0] || '';
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
                            if (!field) continue;
                            if (field.tomselect) {
                                field.tomselect.setValue(value);
                            } else {
                                field.value = value;
                            }
                        }
                    }
                    localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(window.getFormDataObj(form)));

                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success py-2 small shadow-sm mb-4 border-success';
                    alertDiv.innerHTML = `Успех: Данные успешно скопированы.<br><span class="text-dark">Пожалуйста, проверьте данные и нажмите «Сохранить черновик» или «Сдать отчет».</span>`;
                    form.parentNode.insertBefore(alertDiv, form);
                    window.scrollTo({ top: form.offsetTop - 50, behavior: 'smooth' });
                } else {
                    coppAlert('Не удалось загрузить отчет: ' + data.message, 'error');
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = originalText;
                coppAlert('Ошибка сети при загрузке: ' + err, 'error');
            });
    }
})();
