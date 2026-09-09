/**
 * dynamic_fields.js
 * Добавление и удаление динамических групп полей (Sheet Instances)
 */
(function () {
    'use strict';

    window.addSheetInstance = function(btn) {
        if (window.FILL_CONFIG && window.FILL_CONFIG.isLocked) return;
        
        const wrapper = btn.closest('.sheet-content-wrapper') || btn.closest('.mobile-card');
        if (!wrapper) {
            console.error('[addSheetInstance] Не найден родительский wrapper');
            return;
        }
        const container = wrapper.querySelector('.sheet-instances-container');
        if (!container) return;
        
        const items = container.querySelectorAll('.sheet-instance');
        if (items.length === 0) return;
        
        const firstItem = items[0];
        const sheetTitle = wrapper.querySelector('.btn-add-sheet-instance')
                            ?.textContent?.replace(/Добавить еще\s*["«]?|["»]?/gi, '').trim()
                            || 'Специальность';
        const newIdx = items.length + 1;
        
        const savedValues = new Map();
        firstItem.querySelectorAll('select').forEach(sel => {
            savedValues.set(sel.name || sel.id, Array.from(sel.selectedOptions).map(o => o.value));
            if (sel.tomselect) sel.tomselect.destroy();
        });
        firstItem.querySelectorAll('input, textarea').forEach(inp => {
            savedValues.set(inp.name || inp.id, inp.value);
        });
        
        const newItem = firstItem.cloneNode(true);
        
        if (window.initTomSelects) window.initTomSelects(firstItem);
        firstItem.querySelectorAll('select').forEach(sel => {
            const key = sel.name || sel.id;
            const vals = savedValues.get(key);
            if (vals && sel.tomselect) {
                sel.tomselect.setValue(vals.length === 1 ? vals[0] : vals);
            }
        });
        firstItem.querySelectorAll('input, textarea').forEach(inp => {
            const key = inp.name || inp.id;
            if (savedValues.has(key)) inp.value = savedValues.get(key);
        });
        
        newItem.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.type === 'checkbox' || input.type === 'radio') input.checked = false;
            else input.value = '';
        });
        
        newItem.querySelectorAll('.ts-wrapper').forEach(w => w.remove());
        const hiddenRemoveBtn = newItem.querySelector('.remove-sheet-instance');
        if (hiddenRemoveBtn) hiddenRemoveBtn.remove();
        newItem.querySelectorAll('.sheet-instance-divider').forEach(d => d.remove());
        
        newItem.dataset.instIdx = items.length;
        
        const divider = document.createElement('div');
        divider.className = 'sheet-instance-divider';
        divider.innerHTML = `
            <span class="divider-num">${newIdx}</span>
            <span class="divider-label">${sheetTitle}</span>
            <span class="divider-line"></span>
            <button type="button" class="btn btn-outline-danger btn-sm remove-sheet-instance" onclick="removeSheetInstance(this)">
                <i class="bi bi-trash"></i> Удалить блок
            </button>`;
        newItem.insertBefore(divider, newItem.firstChild);
        
        container.appendChild(newItem);
        
        if (window.initTomSelects) window.initTomSelects(newItem);
        if (btn.closest('form')) btn.closest('form').dispatchEvent(new Event('change', {bubbles: true}));
        setTimeout(() => newItem.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    };

    window.removeSheetInstance = function(btn) {
        if (window.FILL_CONFIG && window.FILL_CONFIG.isLocked) return;
        const container = btn.closest('.sheet-instances-container');
        const item = btn.closest('.sheet-instance');
        item.remove();
        
        container.querySelectorAll('.sheet-instance').forEach((it, index) => {
            it.dataset.instIdx = index;
        });
        if (btn.closest('form')) btn.closest('form').dispatchEvent(new Event('change', {bubbles: true}));
    };
})();
