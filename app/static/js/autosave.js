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
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.FILL_CONFIG.csrfToken },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(res => {
                if (res.status === 'success') {
                    showSavedIndicator('Черновик сохранен ☁️');
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
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.FILL_CONFIG.csrfToken },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(res => {
            if (res.status === 'success') {
                btn.innerHTML = '<i class="bi bi-cloud-check-fill me-2"></i>Сохранено ☁️';
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

        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Отправка...';

        fetch(window.FILL_CONFIG.submitUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.FILL_CONFIG.csrfToken },
            body: JSON.stringify(window.getFormDataObj(form))
        })
        .then(res => res.json())
        .then(res => {
            if (res.status === 'success') {
                btn.innerHTML = 'Сдано';
                btn.classList.replace('btn-copp', 'btn-success');
                try { localStorage.removeItem(window.FILL_CONFIG.draftKey); } catch(e) {}
                fetch(window.FILL_CONFIG.draftUrl, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': window.FILL_CONFIG.csrfToken }
                }).catch(() => {});
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
})();
