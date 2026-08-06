/**
 * fill_report.js
 * Логика страницы заполнения отчета.
 *
 * Ожидает наличия в window следующих переменных (задаются в fill_report.html):
 *   - window.FILL_CONFIG.draftKey    — ключ для localStorage
 *   - window.FILL_CONFIG.totalTabs   — кол-во листов (вкладок)
 *   - window.FILL_CONFIG.isPreview   — boolean: режим предпросмотра
 *   - window.FILL_CONFIG.isLocked    — boolean: отчет заблокирован
 *   - window.FILL_CONFIG.submitUrl   — URL для POST-запроса сдачи отчета
 *   - window.FILL_CONFIG.prevDataUrl — URL для загрузки прошлых данных
 *   - window.FILL_CONFIG.csrfToken   — CSRF-токен
 *   - window.schemaTree              — JSON-схема для валидации
 */

(function () {
    'use strict';

    // =========================================================================
    // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    // =========================================================================

    /**
     * Считывает все данные формы в плоский объект.
     * Множественные поля (data-multiple="true") собираются в массив.
     */
    function getFormDataObj(formElement) {
        const formData = new FormData(formElement);
        const dataObj = {};
        const multipleInputs = Array.from(formElement.querySelectorAll('[data-multiple="true"]'));
        const multipleNames = new Set(multipleInputs.map(el => el.name));

        for (const key of new Set(formData.keys())) {
            if (multipleNames.has(key)) {
                dataObj[key] = formData.getAll(key).filter(v => v.trim() !== '');
            } else {
                dataObj[key] = formData.get(key);
            }
        }
        return dataObj;
    }

    // Экспортируем для report_validation.js
    window.getFormDataObj = getFormDataObj;

    // =========================================================================
    // WIZARD (мастер вкладок)
    // =========================================================================

    let currentTabIndex = 0;

    function updateWizardButtons(index) {
        currentTabIndex = index;
        const totalTabs = (window.FILL_CONFIG || {}).totalTabs || 1;
        const btnPrev   = document.getElementById('btn-prev-step');
        const btnNext   = document.getElementById('btn-next-step');
        const btnSubmit = document.getElementById('btn-submit-report');
        if (!btnPrev || !btnNext || !btnSubmit) return;

        const isFirst = currentTabIndex === 0;
        const isLast  = currentTabIndex === totalTabs - 1;
        btnPrev.classList.toggle('d-none', isFirst);
        btnPrev.classList.toggle('d-flex', !isFirst);
        btnNext.classList.toggle('d-none', isLast);
        btnNext.classList.toggle('d-flex', !isLast);
        btnSubmit.classList.toggle('d-none', !isLast);
        btnSubmit.classList.toggle('d-flex', isLast);
    }

    window.nextTab = function () {
        const pane = document.querySelector(`#sheet-${currentTabIndex + 1}`);
        if (pane) {
            for (const input of pane.querySelectorAll('input[required], textarea[required], select[required]')) {
                if (!input.checkValidity()) { input.reportValidity(); return; }
            }
        }
        if (currentTabIndex < (window.FILL_CONFIG || {}).totalTabs - 1) {
            const el = document.querySelector(`button[data-bs-target="#sheet-${currentTabIndex + 2}"]`);
            if (el) bootstrap.Tab.getOrCreateInstance(el).show();
        }
    };

    window.prevTab = function () {
        if (currentTabIndex > 0) {
            const el = document.querySelector(`button[data-bs-target="#sheet-${currentTabIndex}"]`);
            if (el) bootstrap.Tab.getOrCreateInstance(el).show();
        }
    };

    // =========================================================================
    // АВТОСОХРАНЕНИЕ В LOCALSTORAGE
    // =========================================================================

    function setupAutosave(form) {
        const DRAFT_KEY = window.FILL_CONFIG.draftKey;
        let autosaveTimeout, fadeOutTimeout;

        const triggerAutosave = () => {
            if (window.FILL_CONFIG.isPreview) return;
            clearTimeout(autosaveTimeout);
            clearTimeout(fadeOutTimeout);

            const wrap      = document.getElementById('autosave-indicator');
            const indicator = document.getElementById('autosave-time');
            const icon      = document.querySelector('#autosave-indicator i');

            if (wrap && indicator && icon) {
                wrap.style.opacity   = '1';
                indicator.className  = 'text-primary';
                indicator.textContent = 'Сохранение...';
                icon.className = 'spinner-border spinner-border-sm me-1 text-primary';
            }

            autosaveTimeout = setTimeout(() => {
                localStorage.setItem(DRAFT_KEY, JSON.stringify(getFormDataObj(form)));
                if (wrap && indicator && icon) {
                    const now = new Date();
                    const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
                    indicator.className   = 'text-success';
                    indicator.textContent = `Черновик сохранен в ${t}`;
                    icon.className = 'bi bi-check-circle me-1 text-success';
                    fadeOutTimeout = setTimeout(() => { wrap.style.opacity = '0'; }, 3000);
                }
            }, 1000);
        };

        form.addEventListener('input',  triggerAutosave);
        form.addEventListener('change', triggerAutosave); // Tom Select генерирует 'change'
    }

    // =========================================================================
    // РУЧНОЕ СОХРАНЕНИЕ ЧЕРНОВИКА
    // =========================================================================

    window.saveDraftManual = function (btn) {
        const form = document.getElementById('reportForm');
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Сохранение...';
        btn.disabled = true;

        localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(getFormDataObj(form)));

        const indicator = document.getElementById('autosave-time');
        const icon      = document.querySelector('#autosave-indicator i');
        if (indicator && icon) {
            const now = new Date();
            const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
            indicator.textContent = `Сохранено вручную в ${t}`;
            icon.className = 'bi bi-cloud-check-fill me-2 text-success';
        }

        btn.innerHTML = 'Сохранено';
        btn.classList.replace('btn-copp', 'btn-success');
        setTimeout(() => {
            btn.innerHTML = 'Сохранить черновик';
            btn.classList.replace('btn-success', 'btn-copp');
            btn.disabled = false;
        }, 2000);
    };

    // =========================================================================
    // ОТПРАВКА ОТЧЁТА
    // =========================================================================

    window.submitFullForm = function (btn) {
        const form = document.getElementById('reportForm');
        if (!form.reportValidity()) return;

        if (window.runClientValidation && !window.runClientValidation()) {
            coppAlert('Пожалуйста, исправьте ошибки валидации сумм перед отправкой (подсвечены красным).', 'warning');
            return;
        }

        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Отправка...';

        fetch(window.FILL_CONFIG.submitUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.FILL_CONFIG.csrfToken },
            body: JSON.stringify(getFormDataObj(form))
        })
        .then(res => res.json())
        .then(res => {
            if (res.status === 'success') {
                btn.innerHTML = 'Сохранено';
                btn.classList.replace('btn-copp', 'btn-success');
                localStorage.removeItem(window.FILL_CONFIG.draftKey);
                setTimeout(() => { window.location.href = '/'; }, 1000);
            } else {
                coppAlert('Ошибка: ' + res.message, 'error');
                btn.disabled  = false;
                btn.innerHTML = originalHtml;
            }
        })
        .catch(err => {
            coppAlert('Ошибка сети: ' + err, 'error');
            btn.disabled  = false;
            btn.innerHTML = originalHtml;
        });
    };

    // =========================================================================
    // ЗАГРУЗКА ПРОШЛЫХ ДАННЫХ
    // =========================================================================

    window.loadPreviousData = function () {
        const btn = document.getElementById('btn-no-changes');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Загрузка...';

        // 1. Получаем список прошлых отчетов
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

                // Показываем окно подтверждения с названием отчета
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
                        const field = form.elements[name];
                        if (!field) continue;
                        if (field.tomselect) {
                            field.tomselect.setValue(value);
                        } else {
                            field.value = value;
                        }
                    }
                    localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(getFormDataObj(form)));

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


    // =========================================================================
    // ДИНАМИЧЕСКИЕ ПОЛЯ
    // =========================================================================

    window.addDynamicField = function (btn, type, name) {
        const wrapper = btn.closest('.dynamic-field-wrapper');
        const item    = document.createElement('div');
        item.className = 'dynamic-field-item d-flex gap-2 mb-2 align-items-start';

        let inputHtml = '';
        if (type === 'text' || type === 'Текстовое') {
            inputHtml = `<textarea class="form-control" data-multiple="true" name="${name}" rows="2"></textarea>`;
        } else if (type === 'select') {
            const options = JSON.parse(btn.dataset.options || '[]');
            let opts = '<option value="">-- Выберите значение --</option>';
            options.forEach(opt => { opts += `<option value="${opt}">${opt}</option>`; });
            inputHtml = `<select class="form-select" data-multiple="true" name="${name}">${opts}</select>`;
        } else {
            inputHtml = `<input type="number" class="form-control" data-multiple="true" name="${name}" value="" min="0" step="any">`;
        }

        item.innerHTML = inputHtml + `<button type="button" class="btn btn-outline-danger px-3 mt-1 remove-dynamic-field" onclick="removeDynamicField(this)"><i class="bi bi-trash"></i></button>`;
        wrapper.insertBefore(item, btn);
        if (window.initTomSelects) window.initTomSelects(item);
    };

    window.removeDynamicField = function (btn) {
        btn.closest('.dynamic-field-item').remove();
    };

    // =========================================================================
    // ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ СТРАНИЦЫ
    // =========================================================================

    document.addEventListener('DOMContentLoaded', () => {
        const form   = document.getElementById('reportForm');
        const config = window.FILL_CONFIG || {};

        // Bootstrap Tooltips
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el, { trigger: 'hover' });
        });

        // Мастер вкладок
        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach((tab, index) => {
            tab.addEventListener('shown.bs.tab', () => {
                updateWizardButtons(index);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
        updateWizardButtons(0);

        // Восстановление черновика
        if (!config.isLocked && !config.isPreview && config.draftKey) {
            const savedDraft = localStorage.getItem(config.draftKey);
            if (savedDraft) {
                try {
                    const data = JSON.parse(savedDraft);
                    let restored = false;
                    for (const [name, value] of Object.entries(data)) {
                        if (name === 'csrf_token') continue;
                        const field = form.elements[name];
                        if (field && (!field.value || field.value === '')) {
                            field.value = value;
                            restored = true;
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
            setupAutosave(form);
        }

        // Клиентская валидация иерархии сумм
        if (typeof initRealTimeValidation === 'function') {
            window.runClientValidation = initRealTimeValidation(window.schemaTree, getFormDataObj, form);
        }
    });

})();
