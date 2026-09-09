/**
 * wizard.js
 * Логика переключения вкладок (шагов)
 */
(function () {
    'use strict';
    let currentTabIndex = 0;

    window.updateWizardButtons = function(index) {
        currentTabIndex = index;
        const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
        const totalTabs = tabs.length;
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
    };

    window.nextTab = function () {
        const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
        if (currentTabIndex >= tabs.length) return;
        
        const currentTabBtn = tabs[currentTabIndex];
        const targetSelector = currentTabBtn.dataset.bsTarget;
        const pane = document.querySelector(targetSelector);
        
        if (pane) {
            for (const input of pane.querySelectorAll('input[required], textarea[required], select[required]')) {
                if (!input.checkValidity()) { input.reportValidity(); return; }
            }
        }
        
        if (currentTabIndex < tabs.length - 1) {
            bootstrap.Tab.getOrCreateInstance(tabs[currentTabIndex + 1]).show();
        }
    };

    window.prevTab = function () {
        if (currentTabIndex > 0) {
            const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
            bootstrap.Tab.getOrCreateInstance(tabs[currentTabIndex - 1]).show();
        }
    };
})();
