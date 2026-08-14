/**
 * Модуль для клиентской иерархической валидации данных формы отчета.
 */

function sumFieldValues(val) {
    if (val === null || val === undefined) return 0.0;
    if (Array.isArray(val)) {
        let total = 0.0;
        for (let v of val) {
            if (v !== null && String(v).trim() !== '') {
                let parsed = parseFloat(v);
                if (!isNaN(parsed)) total += parsed;
            }
        }
        return total;
    } else {
        if (String(val).trim() !== '') {
            let parsed = parseFloat(val);
            if (!isNaN(parsed)) return parsed;
        }
    }
    return 0.0;
}

/**
 * Валидация всего дерева
 */
function validateHierarchy(schemaTree, dataObj) {
    for (let sheet of schemaTree) {
        const tree = sheet.fields_tree || [];
        const result = _validateNodes(tree, dataObj);
        if (!result.isValid) {
            return result;
        }
    }
    return { isValid: true, errorMsg: "" };
}

function _validateNodes(nodes, dataObj) {
    for (let node of nodes) {
        const field = node.field || {};
        const children = node.children || [];
        
        // Рекурсивно проверяем детей
        const childResult = _validateNodes(children, dataObj);
        if (!childResult.isValid) return childResult;
        
        if (children.length === 0) continue;
        
        if (field.type === 'text' || field.type === 'Текстовое' || field.type === 'select' || field.validateSum === false) {
            continue;
        }
        
        const parentValRaw = dataObj[field.name];
        if (parentValRaw === undefined || parentValRaw === null || String(parentValRaw).trim() === '') {
            continue;
        }
        if (Array.isArray(parentValRaw) && parentValRaw.length === 0) {
            continue;
        }
        
        const parentSum = sumFieldValues(parentValRaw);
        let childrenSum = 0.0;
        
        for (let child of children) {
            const childField = child.field || {};
            if (childField.type !== 'text' && childField.type !== 'Текстовое') {
                const childVal = dataObj[childField.name];
                childrenSum += sumFieldValues(childVal);
            }
        }
        
        if (childrenSum > parentSum + 0.0001) {
            return {
                isValid: false, 
                errorMsg: `Сумма вложенных полей (${childrenSum}) превышает значение родительского поля «${field.label || 'Без названия'}» (${parentSum}).`,
                invalidParentName: field.name
            };
        }
    }
    return { isValid: true, errorMsg: "" };
}

/**
 * Инициализация проверки на лету
 */
function initRealTimeValidation(schemaTree, getFormDataObjFunc, formElement) {
    
    function clearAllValidationErrors() {
        formElement.querySelectorAll('.hierarchy-invalid').forEach(el => {
            el.classList.remove('is-invalid', 'hierarchy-invalid');
        });
        formElement.querySelectorAll('.hierarchy-error-feedback').forEach(el => {
            el.remove();
        });
    }

    function runValidation() {
        clearAllValidationErrors();
        const dataObj = getFormDataObjFunc(formElement);
        const result = validateHierarchy(schemaTree, dataObj);
        
        if (!result.isValid && result.invalidParentName) {
            // Ищем все инпуты этого родителя и подсвечиваем их
            const parentInputs = formElement.querySelectorAll(`input[name="${result.invalidParentName}"]`);
            parentInputs.forEach(input => {
                input.classList.add('is-invalid', 'hierarchy-invalid');
                
                // Добавляем текст ошибки если его еще нет
                let nextSibling = input.nextElementSibling;
                if (!nextSibling || !nextSibling.classList.contains('hierarchy-error-feedback')) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback hierarchy-error-feedback d-block fw-bold';
                    errorDiv.textContent = result.errorMsg;
                    input.parentNode.insertBefore(errorDiv, input.nextSibling);
                }
            });
        }
        return result.isValid;
    }

    // Делегирование событий на форму — работает для ВСЕХ инпутов включая динамически добавленные
    formElement.addEventListener('input', function(e) {
        if (e.target.matches('input[type="number"], input[type="text"]')) {
            runValidation();
        }
    });
    
    // Возвращаем функцию ручного запуска валидации (для вызова перед отправкой)
    return runValidation;
}
