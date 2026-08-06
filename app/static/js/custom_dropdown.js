/**
 * custom_dropdown.js — ЦОПП РАС
 * Кастомный дроплаун для нативных <select>.
 *
 * Пропускает:
 *   - multiple select (Tom Select)
 *   - select с классом form-select ЕСЛИ Tom Select доступен (он их уже стилизует)
 *   - data-no-custom="1"
 *   - уже инициализированные
 *   - обёрнутые в .ts-wrapper (Tom Select)
 */
(function () {
    'use strict';

    const SVG_SORT    = `<svg class="dd-icon" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M3.5 3.5a.5.5 0 0 0-1 0v8.793l-1.146-1.147a.5.5 0 0 0-.708.708l2 1.999.007.007a.497.497 0 0 0 .7-.006l2-2a.5.5 0 0 0-.707-.708L3.5 12.293V3.5zm4 .5a.5.5 0 0 1 0-1h1a.5.5 0 0 1 0 1h-1zm0 3a.5.5 0 0 1 0-1h3a.5.5 0 0 1 0 1h-3zm0 3a.5.5 0 0 1 0-1h5a.5.5 0 0 1 0 1h-5zM7 12.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 0-1h-7a.5.5 0 0 0-.5.5z"/></svg>`;
    const SVG_CHEVRON = `<svg class="dd-chevron" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/></svg>`;
    const SVG_CHECK   = `<svg class="dd-check" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>`;

    function shouldSkip(selectEl) {
        if (!selectEl || selectEl.tagName !== 'SELECT')    return true;
        if (selectEl.multiple)                              return true;
        if (selectEl.dataset.noCustom)                     return true;
        if (selectEl.dataset.customDropdown)               return true;
        if (selectEl.closest('.ts-wrapper'))               return true;
        if (selectEl.closest('.custom-dropdown'))          return true;
        if (selectEl.classList.contains('swal2-select'))   return true;
        // Если Tom Select доступен и это form-select — Tom Select сам его стилизует
        if (typeof TomSelect !== 'undefined' && selectEl.classList.contains('form-select')) return true;
        return false;
    }

    window.initCustomDropdown = function (selectEl) {
        if (shouldSkip(selectEl)) return;

        selectEl.dataset.customDropdown = '1';
        selectEl.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-dropdown';
        selectEl.parentNode.insertBefore(wrapper, selectEl);
        wrapper.appendChild(selectEl);

        const trigger = document.createElement('div');
        trigger.className = 'custom-dropdown-trigger';
        trigger.setAttribute('role', 'button');
        trigger.setAttribute('tabindex', '0');
        trigger.innerHTML = SVG_SORT + `<span class="dd-text"></span>` + SVG_CHEVRON;
        wrapper.insertBefore(trigger, selectEl);

        const menu = document.createElement('div');
        menu.className = 'custom-dropdown-menu';
        wrapper.appendChild(menu);

        function buildMenu() {
            menu.innerHTML = '';
            const sel = selectEl.options[selectEl.selectedIndex];
            if (sel) trigger.querySelector('.dd-text').textContent = sel.text;
            Array.from(selectEl.options).forEach(opt => {
                const item = document.createElement('div');
                item.className = 'custom-dropdown-item' + (opt.selected ? ' is-selected' : '');
                item.dataset.value = opt.value;
                item.innerHTML = SVG_CHECK + `<span class="dd-item-text">${opt.text}</span>`;
                item.addEventListener('click', () => {
                    selectEl.value = opt.value;
                    selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                    selectEl.dispatchEvent(new Event('input',  { bubbles: true }));
                    menu.querySelectorAll('.custom-dropdown-item').forEach(i => i.classList.remove('is-selected'));
                    item.classList.add('is-selected');
                    trigger.querySelector('.dd-text').textContent = opt.text;
                    close();
                });
                menu.appendChild(item);
            });
        }

        buildMenu();
        new MutationObserver(buildMenu).observe(selectEl, { childList: true, subtree: true, attributes: true });

        function open() {
            document.querySelectorAll('.custom-dropdown-trigger.is-open').forEach(t => {
                if (t !== trigger) {
                    t.classList.remove('is-open');
                    t.closest('.custom-dropdown')?.querySelector('.custom-dropdown-menu')?.classList.remove('is-open');
                }
            });
            trigger.classList.add('is-open');
            menu.classList.add('is-open');
        }
        function close() {
            trigger.classList.remove('is-open');
            menu.classList.remove('is-open');
        }

        trigger.addEventListener('click', e => { e.stopPropagation(); menu.classList.contains('is-open') ? close() : open(); });
        trigger.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); menu.classList.contains('is-open') ? close() : open(); }
            if (e.key === 'Escape') close();
        });
        document.addEventListener('click', close);
        menu.addEventListener('click', e => e.stopPropagation());
    };

    function initAll() {
        document.querySelectorAll('select').forEach(window.initCustomDropdown);
    }

    // Запускаем после того как Tom Select уже инициализировался
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(initAll, 50));
    } else {
        setTimeout(initAll, 50);
    }

    // MutationObserver для динамических select (конструктор полей, AJAX)
    new MutationObserver(mutations => {
        mutations.forEach(m => m.addedNodes.forEach(node => {
            if (node.nodeType !== 1) return;
            if (node.tagName === 'SELECT') setTimeout(() => window.initCustomDropdown(node), 50);
            node.querySelectorAll?.('select').forEach(s => setTimeout(() => window.initCustomDropdown(s), 50));
        }));
    }).observe(document.documentElement, { childList: true, subtree: true });

})();
