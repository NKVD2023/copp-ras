// JS logic for Period Selector

class PeriodSelector {
    constructor(prefix, defaultDataStr) {
        this.prefix = prefix;
        this.typeSelect = document.getElementById(`${prefix}Type`);
        this.fieldsContainer = document.getElementById(`${prefix}Fields`);
        this.textInput = document.getElementById(`${prefix}Text`);
        this.dataInput = document.getElementById(`${prefix}Data`);
        
        let defaultData = null;
        try {
            if (defaultDataStr && defaultDataStr !== 'None' && defaultDataStr !== 'null') {
                defaultData = JSON.parse(defaultDataStr);
            }
        } catch(e) { console.error(e); }

        this.typeSelect.addEventListener('change', () => this.renderFields());
        
        // Initialize
        if (defaultData && defaultData.type) {
            this.typeSelect.value = defaultData.type;
            this.renderFields(defaultData);
        } else {
            // Default to empty or fallback to old string parsing? Let's just leave it empty.
        }
    }

    renderFields(defaultData = null) {
        const type = this.typeSelect.value;
        this.fieldsContainer.innerHTML = '';
        
        const currentYear = new Date().getFullYear();
        let html = '';

        const generateYearOptions = (selected) => {
            let opts = '';
            for(let y = currentYear - 5; y <= 2100; y++) {
                opts += `<option value="${y}" ${selected == y ? 'selected' : ''}>${y}</option>`;
            }
            return opts;
        };

        if (type === 'quarter') {
            const selectedQ = defaultData ? defaultData.quarter : 1;
            const selectedY = defaultData ? defaultData.year : currentYear;
            html = `
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="quarter">
                    <option value="I" ${selectedQ=='I'?'selected':''}>I</option>
                    <option value="II" ${selectedQ=='II'?'selected':''}>II</option>
                    <option value="III" ${selectedQ=='III'?'selected':''}>III</option>
                    <option value="IV" ${selectedQ=='IV'?'selected':''}>IV</option>
                </select>
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="year">
                    ${generateYearOptions(selectedY)}
                </select>
            `;
        } else if (type === 'month') {
            const months = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
            const selectedM = defaultData ? defaultData.month : months[0];
            const selectedY = defaultData ? defaultData.year : currentYear;
            let mOpts = months.map(m => `<option value="${m}" ${selectedM==m?'selected':''}>${m}</option>`).join('');
            html = `
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="month">${mOpts}</select>
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="year">${generateYearOptions(selectedY)}</select>
            `;
        } else if (type === 'halfyear') {
            const selectedH = defaultData ? defaultData.halfyear : 'I';
            const selectedY = defaultData ? defaultData.year : currentYear;
            html = `
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="halfyear">
                    <option value="I" ${selectedH=='I'?'selected':''}>I</option>
                    <option value="II" ${selectedH=='II'?'selected':''}>II</option>
                </select>
                <select class="form-select form-select-sm w-auto period-dynamic" data-key="year">${generateYearOptions(selectedY)}</select>
            `;
        } else if (type === 'year') {
            const selectedY = defaultData ? defaultData.year : currentYear;
            html = `<select class="form-select form-select-sm w-auto period-dynamic" data-key="year">${generateYearOptions(selectedY)}</select>`;
        } else if (type === 'academic') {
            const selectedY = defaultData ? defaultData.year : currentYear;
            let opts = '';
            for(let y = currentYear - 5; y <= 2100; y++) {
                opts += `<option value="${y}" ${selectedY == y ? 'selected' : ''}>${y}/${y+1}</option>`;
            }
            html = `<select class="form-select form-select-sm w-auto period-dynamic" data-key="year">${opts}</select>`;
        } else if (type === 'week') {
            const selectedStart = defaultData ? defaultData.start : '';
            const selectedEnd = defaultData ? defaultData.end : '';
            html = `
                <div class="d-flex align-items-center gap-1">
                    <span class="small text-muted">С</span>
                    <input type="date" class="form-control form-control-sm period-dynamic" data-key="start" value="${selectedStart}">
                    <span class="small text-muted">По</span>
                    <input type="date" class="form-control form-control-sm period-dynamic" data-key="end" value="${selectedEnd}">
                </div>
            `;
        } else if (type === 'date') {
            const selectedDate = defaultData ? defaultData.date : '';
            html = `<input type="date" class="form-control form-control-sm w-auto period-dynamic" data-key="date" value="${selectedDate}">`;
        } else if (type === 'range') {
            const selectedStart = defaultData ? defaultData.start : '';
            const selectedEnd = defaultData ? defaultData.end : '';
            html = `
                <div class="d-flex align-items-center gap-1">
                    <span class="small text-muted">От</span>
                    <input type="date" class="form-control form-control-sm period-dynamic" data-key="start" value="${selectedStart}">
                    <span class="small text-muted">До</span>
                    <input type="date" class="form-control form-control-sm period-dynamic" data-key="end" value="${selectedEnd}">
                </div>
            `;
        }

        this.fieldsContainer.innerHTML = html;
        
        const dynamics = this.fieldsContainer.querySelectorAll('.period-dynamic');
        dynamics.forEach(el => {
            el.addEventListener('change', () => this.updateValues());
            el.addEventListener('input', () => this.updateValues());
        });

        this.updateValues();
    }

    updateValues() {
        const type = this.typeSelect.value;
        const dynamics = this.fieldsContainer.querySelectorAll('.period-dynamic');
        const data = { type: type };
        dynamics.forEach(el => {
            data[el.dataset.key] = el.value;
        });

        this.dataInput.value = JSON.stringify(data);

        let text = '';
        if (type === 'quarter') text = `${data.quarter} квартал ${data.year}`;
        else if (type === 'month') text = `${data.month} ${data.year}`;
        else if (type === 'halfyear') text = `${data.halfyear} полугодие ${data.year}`;
        else if (type === 'year') text = `${data.year} год`;
        else if (type === 'academic') text = `${data.year}/${parseInt(data.year)+1} учебный год`;
        else if (type === 'week') {
            if (data.start && data.end) {
                const s = data.start.split('-').reverse().join('.');
                const e = data.end.split('-').reverse().join('.');
                text = `Неделя с ${s} по ${e}`;
            } else text = 'Неделя (даты не выбраны)';
        }
        else if (type === 'date') {
            if (data.date) {
                text = data.date.split('-').reverse().join('.');
            } else text = 'Дата не выбрана';
        }
        else if (type === 'range') {
            if (data.start && data.end) {
                const s = data.start.split('-').reverse().join('.');
                const e = data.end.split('-').reverse().join('.');
                text = `${s} - ${e}`;
            } else text = 'Период не выбран';
        }
        
        this.textInput.value = text;
        
        const displayEl = document.getElementById(`${this.prefix}Display`);
        if (displayEl) {
            displayEl.textContent = text;
        }
    }
}

window.periodSelectors = {};
window.initPeriodSelector = function(prefix, defaultDataStr) {
    window.periodSelectors[prefix] = new PeriodSelector(prefix, defaultDataStr);
};
