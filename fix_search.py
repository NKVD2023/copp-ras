import re

with open("app/templates/user_tabs/reports_tabs.html", "r") as f:
    content = f.read()

# 1. Insert the unified search container before tab-content
container_html = """
        <div id="unifiedSearchContainer" class="row g-4 d-none mb-4"></div>
        <div id="unifiedEmptyState" class="col-12 d-none mb-4">
            <div class="text-center py-5 text-muted bg-white rounded border d-flex flex-column align-items-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#e2e8f0" class="mb-3" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z"/></svg>
                <span class="small">По вашему запросу ничего не найдено.</span>
            </div>
        </div>
        <div class="tab-content" id="mainTabContent">
"""

content = content.replace('<div class="tab-content">', container_html)

# 2. Update the Javascript logic
old_js = """
                let searchTimeout;
                function applyFilterAndSort() {
                    if (!searchInput) return;
                    clearTimeout(searchTimeout);
                    
                    const query = searchInput.value.toLowerCase().trim();
                    const sortVal = sortSelect ? sortSelect.value : '';
                    
                    const sections = [
                        {id: 'unfilledContainer', paneId: 'unfilledTab'},
                        {id: 'overdueContainer', paneId: 'overdueTab'},
                        {id: 'filledContainer', paneId: 'filledTab'},
                        {id: 'filesContainer', paneId: 'filesTab'}
                    ];
                    
                    // Fade out rows
                    sections.forEach(sec => {
                        const container = document.getElementById(sec.id);
                        if (container) container.classList.add('is-filtering');
                    });
                    
                    searchTimeout = setTimeout(() => {
                        if (query.length > 0) {
                            document.body.classList.add('search-active');
                            
                            sections.forEach(sec => {
                                const hasVisible = processContainer(sec.id, query, sortVal);
                                const pane = document.getElementById(sec.paneId);
                                if (pane) {
                                    pane.classList.add('d-block');
                                    const title = pane.querySelector('.search-section-title');
                                    if (title) {
                                        title.classList.remove('show-title');
                                        title.classList.add('d-none');
                                    }
                                    pane.style.display = hasVisible ? 'block' : 'none';
                                }
                            });
                        } else {
                            // Очистка поиска
                            document.body.classList.remove('search-active');
                            
                            sections.forEach(sec => {
                                processContainer(sec.id, '', sortVal);
                                const pane = document.getElementById(sec.paneId);
                                if (pane) {
                                    pane.classList.remove('d-block');
                                    pane.style.display = ''; // let bootstrap manage it
                                    const title = pane.querySelector('.search-section-title');
                                    if (title) {
                                        title.classList.remove('show-title');
                                        title.classList.add('d-none');
                                    }
                                }
                            });
                        }
                        
                        // Fade in rows
                        setTimeout(() => {
                            sections.forEach(sec => {
                                const container = document.getElementById(sec.id);
                                if (container) container.classList.remove('is-filtering');
                            });
                        }, 50);
                        
                    }, 300); // 300ms matches the CSS opacity transition duration
                }
                
                function processContainer(containerId, query, sortVal) {
                    const container = document.getElementById(containerId);
                    if (!container) return false;
                    let items = Array.from(container.querySelectorAll('.user-report-item'));
                    let visibleCount = 0;
                    
                    items.forEach(item => {
                        const title = item.getAttribute('data-title') || '';
                        if (title.includes(query)) {
                            item.classList.remove('search-hidden');
                            item.style.display = ''; // Ensure it's not hidden
                            visibleCount++;
                        } else {
                            item.classList.add('search-hidden');
                            // Let CSS handle the hiding (max-height/max-width: 0, opacity: 0)
                        }
                    });
                    
                    const emptyState = container.querySelector('.empty-state');
                    if (emptyState) {
                        if (query.length > 0) {
                            emptyState.style.display = 'none';
                        } else {
                            emptyState.style.display = (items.length === 0) ? '' : 'none';
                        }
                    }
                    
                    // Simple sort implementation
                    if (sortVal && items.length > 0) {
                        items.sort((a, b) => {
                            if (sortVal === 'name_asc') return a.getAttribute('data-title').localeCompare(b.getAttribute('data-title'));
                            if (sortVal === 'name_desc') return b.getAttribute('data-title').localeCompare(a.getAttribute('data-title'));
                            
                            const d1 = a.getAttribute('data-deadline') || '2099-12-31';
                            const d2 = b.getAttribute('data-deadline') || '2099-12-31';
                            if (sortVal === 'deadline_asc') return d1.localeCompare(d2);
                            if (sortVal === 'deadline_desc') return d2.localeCompare(d1);
                            
                            const id1 = parseInt(a.getAttribute('data-id')) || 0;
                            const id2 = parseInt(b.getAttribute('data-id')) || 0;
                            if (sortVal === 'id_desc') return id2 - id1;
                            return 0;
                        });
                        
                        items.forEach(item => container.appendChild(item));
                    }
                    
                    return visibleCount > 0;
                }
"""

new_js = """
                let searchTimeout;
                
                // Initialize original containers
                document.querySelectorAll('.user-report-item').forEach(item => {
                    if (item.closest('.filter-row')) {
                        item.setAttribute('data-original-container', item.closest('.filter-row').id);
                    }
                });
                
                function applyFilterAndSort() {
                    if (!searchInput) return;
                    clearTimeout(searchTimeout);
                    
                    const query = searchInput.value.toLowerCase().trim();
                    const sortVal = sortSelect ? sortSelect.value : '';
                    
                    const sections = ['unfilledContainer', 'overdueContainer', 'filledContainer', 'filesContainer'];
                    const unifiedContainer = document.getElementById('unifiedSearchContainer');
                    const unifiedEmpty = document.getElementById('unifiedEmptyState');
                    const mainTabs = document.getElementById('mainTabContent');
                    
                    searchTimeout = setTimeout(() => {
                        if (query.length > 0) {
                            document.body.classList.add('search-active');
                            
                            // Скрыть табы, показать единый контейнер
                            if (mainTabs) mainTabs.classList.add('d-none');
                            unifiedContainer.classList.remove('d-none');
                            unifiedEmpty.classList.add('d-none');
                            
                            let allItems = Array.from(document.querySelectorAll('.user-report-item'));
                            let visibleItems = [];
                            
                            allItems.forEach(item => {
                                const title = item.getAttribute('data-title') || '';
                                if (title.includes(query)) {
                                    item.style.display = '';
                                    item.classList.remove('search-hidden');
                                    visibleItems.push(item);
                                    unifiedContainer.appendChild(item); // Move to unified container
                                } else {
                                    item.style.display = 'none';
                                    item.classList.add('search-hidden');
                                    unifiedContainer.appendChild(item);
                                }
                            });
                            
                            if (visibleItems.length === 0) {
                                unifiedEmpty.classList.remove('d-none');
                            }
                            
                            // Sort in unified container
                            if (sortVal && visibleItems.length > 0) {
                                visibleItems.sort((a, b) => {
                                    if (sortVal === 'name_asc') return a.getAttribute('data-title').localeCompare(b.getAttribute('data-title'));
                                    if (sortVal === 'name_desc') return b.getAttribute('data-title').localeCompare(a.getAttribute('data-title'));
                                    const d1 = a.getAttribute('data-deadline') || '2099-12-31';
                                    const d2 = b.getAttribute('data-deadline') || '2099-12-31';
                                    if (sortVal === 'deadline_asc') return d1.localeCompare(d2);
                                    if (sortVal === 'deadline_desc') return d2.localeCompare(d1);
                                    const id1 = parseInt(a.getAttribute('data-id')) || 0;
                                    const id2 = parseInt(b.getAttribute('data-id')) || 0;
                                    if (sortVal === 'id_desc') return id2 - id1;
                                    return 0;
                                });
                                visibleItems.forEach(item => unifiedContainer.appendChild(item));
                            }
                            
                        } else {
                            // Очистка поиска: вернуть элементы в их оригинальные контейнеры
                            document.body.classList.remove('search-active');
                            
                            if (mainTabs) mainTabs.classList.remove('d-none');
                            unifiedContainer.classList.add('d-none');
                            unifiedEmpty.classList.add('d-none');
                            
                            let allItems = Array.from(document.querySelectorAll('.user-report-item'));
                            allItems.forEach(item => {
                                item.style.display = '';
                                item.classList.remove('search-hidden');
                                const origId = item.getAttribute('data-original-container');
                                const origContainer = document.getElementById(origId);
                                if (origContainer) {
                                    origContainer.appendChild(item);
                                }
                            });
                            
                            // Сортировка внутри оригинальных контейнеров
                            sections.forEach(secId => {
                                const container = document.getElementById(secId);
                                if (!container) return;
                                
                                let items = Array.from(container.querySelectorAll('.user-report-item'));
                                
                                const emptyState = container.querySelector('.empty-state');
                                if (emptyState) {
                                    emptyState.style.display = (items.length === 0) ? '' : 'none';
                                }
                                
                                if (sortVal && items.length > 0) {
                                    items.sort((a, b) => {
                                        if (sortVal === 'name_asc') return a.getAttribute('data-title').localeCompare(b.getAttribute('data-title'));
                                        if (sortVal === 'name_desc') return b.getAttribute('data-title').localeCompare(a.getAttribute('data-title'));
                                        const d1 = a.getAttribute('data-deadline') || '2099-12-31';
                                        const d2 = b.getAttribute('data-deadline') || '2099-12-31';
                                        if (sortVal === 'deadline_asc') return d1.localeCompare(d2);
                                        if (sortVal === 'deadline_desc') return d2.localeCompare(d1);
                                        const id1 = parseInt(a.getAttribute('data-id')) || 0;
                                        const id2 = parseInt(b.getAttribute('data-id')) || 0;
                                        if (sortVal === 'id_desc') return id2 - id1;
                                        return 0;
                                    });
                                    items.forEach(item => container.appendChild(item));
                                }
                            });
                        }
                    }, 100);
                }
"""

if old_js in content:
    content = content.replace(old_js, new_js)
    with open("app/templates/user_tabs/reports_tabs.html", "w") as f:
        f.write(content)
    print("JS logic updated successfully.")
else:
    print("Could not find the old JS block to replace. Here's what I searched for:")
    print(repr(old_js[:100]))

