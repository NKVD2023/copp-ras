/**
 * autosave.js
 * Автосохранение черновиков, ручное сохранение и отправка отчета
 */
(function () {
    'use strict';

    window.setupAutosave = function(form) {
        const DRAFT_KEY = window.FILL_CONFIG.draftKey;
        let localSaveTimeout, cloudSaveTimeout, fadeOutTimeout;

        const showSavingIndicator = () => {
            const wrap      = document.getElementById('autosave-indicator');
            const indicator = document.getElementById('autosave-time');
            const icon      = document.querySelector('#autosave-indicator i');
            if (wrap && indicator && icon) {
                wrap.style.opacity   = '1';
                indicator.className  = 'text-primary';
                indicator.textContent = 'Сохранение...';
                icon.className = 'spinner-border spinner-border-sm me-1 text-primary';
            }
        };

        const showSavedIndicator = (label) => {
            const wrap      = document.getElementById('autosave-indicator');
            const indicator = document.getElementById('autosave-time');
            const icon      = document.querySelector('#autosave-indicator i');
            if (wrap && indicator && icon) {
                const now = new Date();
                const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
                indicator.className   = 'text-success';
                indicator.textContent = `${label} в ${t}`;
                icon.className = 'bi bi-cloud-check-fill me-1 text-success';
                clearTimeout(fadeOutTimeout);
                fadeOutTimeout = setTimeout(() => { wrap.style.opacity = '0'; }, 4000);
            }
        };

        const saveToLocalStorage = () => {
            try {
                localStorage.setItem(DRAFT_KEY, JSON.stringify(window.getFormDataObj(form)));
            } catch(e) { /* ignore quota errors */ }
        };

        const saveToCloud = () => {
            if (window.FILL_CONFIG.isPreview || window.FILL_CONFIG.isLocked) return;
            const data = window.getFormDataObj(form);
            showSavingIndicator();
            fetch(window.FILL_CONFIG.draftUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': window.FILL_CONFIG.csrfToken
                },
                body: JSON.stringify(data)
            })
            .then(r => {
                if (r.status === 401 || (r.redirected && r.url && r.url.includes('/auth/login'))) {
                    saveToLocalStorage();
                    return null;
                }
                const contentType = r.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                    throw new Error('Non-JSON response');
                }
                return r.json();
            })
            .then(res => {
                if (!res) return;
                if (res.status === 'success') {
                    showSavedIndicator('Черновик сохранен');
                    saveToLocalStorage();
                }
            })
            .catch(() => {
                saveToLocalStorage();
                const wrap      = document.getElementById('autosave-indicator');
                const indicator = document.getElementById('autosave-time');
                const icon      = document.querySelector('#autosave-indicator i');
                if (wrap && indicator && icon) {
                    indicator.className   = 'text-warning';
                    indicator.textContent = 'Сохранено локально (нет сети)';
                    icon.className = 'bi bi-cloud-slash me-1 text-warning';
                    clearTimeout(fadeOutTimeout);
                    fadeOutTimeout = setTimeout(() => { wrap.style.opacity = '0'; }, 4000);
                }
            });
        };

        const triggerAutosave = () => {
            if (window.FILL_CONFIG.isPreview) return;
            clearTimeout(localSaveTimeout);
            localSaveTimeout = setTimeout(saveToLocalStorage, 1000);
            clearTimeout(cloudSaveTimeout);
            cloudSaveTimeout = setTimeout(saveToCloud, 45000);
        };

        form.addEventListener('input',  triggerAutosave);
        form.addEventListener('change', triggerAutosave);
    };

    window.saveDraftManual = function (btn) {
        const form = document.getElementById('reportForm');
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Сохранение...';
        btn.disabled = true;

        const data = window.getFormDataObj(form);

        try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(data)); } catch(e) {}

        fetch(window.FILL_CONFIG.draftUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.FILL_CONFIG.csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(r => {
            if (r.status === 401 || (r.redirected && r.url && r.url.includes('/auth/login'))) {
                try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(data)); } catch(e) {}
                window.location.href = '/auth/login';
                return null;
            }
            const contentType = r.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                throw new Error('Non-JSON response');
            }
            return r.json();
        })
        .then(res => {
            if (!res) return;
            if (res.status === 'success') {
                btn.innerHTML = '<i class="bi bi-cloud-check-fill me-2"></i>Сохранено';
                btn.classList.replace('btn-copp', 'btn-success');
            } else {
                btn.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>Ошибка';
                btn.classList.replace('btn-copp', 'btn-warning');
            }
        })
        .catch(() => {
            btn.innerHTML = '<i class="bi bi-floppy me-2"></i>Сохранено локально';
            btn.classList.replace('btn-copp', 'btn-warning');
        })
        .finally(() => {
            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.classList.replace('btn-success', 'btn-copp');
                btn.classList.replace('btn-warning', 'btn-copp');
                btn.disabled = false;
            }, 2500);
        });
    };

    window.submitFullForm = function (btn) {
        const form = document.getElementById('reportForm');
        if (!form.reportValidity()) return;

        if (window.runClientValidation && !window.runClientValidation()) {
            coppAlert('Пожалуйста, исправьте ошибки валидации сумм перед отправкой (подсвечены красным).', 'warning');
            return;
        }

        const formDataObj = window.getFormDataObj(form);
        // Немедленная страховка данных в localStorage перед началом отправки
        try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(formDataObj)); } catch(e) {}

        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Отправка...';

        fetch(window.FILL_CONFIG.submitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.FILL_CONFIG.csrfToken
            },
            body: JSON.stringify(formDataObj)
        })
        .then(async r => {
            // Перенаправление на авторизацию или истечение сессии
            if (r.status === 401 || (r.redirected && r.url && r.url.includes('/auth/login'))) {
                try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(formDataObj)); } catch(e) {}
                coppAlert('Срок вашей сессии истек. Данные отчета сохранены в браузере. Вы будете перенаправлены на страницу входа.', 'warning');
                setTimeout(() => { window.location.href = '/auth/login'; }, 2500);
                return null;
            }

            const contentType = r.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(formDataObj)); } catch(e) {}
                if (r.status === 502 || r.status === 503 || r.status === 504) {
                    throw new Error('Сервер временно недоступен или перезагружается (код ' + r.status + '). Ваши данные сохранены в браузере, повторите отправку через 15 секунд.');
                }
                if (r.status === 403) {
                    throw new Error('Доступ ограничен или срок сдачи отчета завершен. Ваши данные сохранены в браузере.');
                }
                if (r.status === 400) {
                    throw new Error('Срок действия формы истек. Ваши данные сохранены в браузере. Пожалуйста, обновите страницу.');
                }
                throw new Error('Ошибка сервера (код ' + r.status + '). Данные отчета надежно сохранены в браузере.');
            }

            let res;
            try {
                res = await r.json();
            } catch (jsonErr) {
                try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(formDataObj)); } catch(e) {}
                throw new Error('Некорректный ответ сервера. Ваши данные сохранены в браузере.');
            }

            return { ok: r.ok, status: r.status, data: res };
        })
        .then(result => {
            if (!result) return;
            const { ok, data } = result;
            if (ok && data && data.status === 'success') {
                btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Сдано';
                btn.classList.replace('btn-copp', 'btn-success');
                try { localStorage.removeItem(window.FILL_CONFIG.draftKey); } catch(e) {}
                fetch(window.FILL_CONFIG.draftUrl, {
                    method: 'DELETE',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': window.FILL_CONFIG.csrfToken }
                }).catch(() => {});
                setTimeout(() => { window.location.href = '/'; }, 1000);
            } else {
                const msg = (data && data.message) ? data.message : 'Не удалось отправить отчет';
                coppAlert(msg, 'error');
                btn.disabled  = false;
                btn.innerHTML = originalHtml;
            }
        })
        .catch(err => {
            try { localStorage.setItem(window.FILL_CONFIG.draftKey, JSON.stringify(formDataObj)); } catch(e) {}
            const msg = (err && err.message) ? err.message : String(err);
            coppAlert(msg, 'error');
            btn.disabled  = false;
            btn.innerHTML = originalHtml;
        });
    };
})();

