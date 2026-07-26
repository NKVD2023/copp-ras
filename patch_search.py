import re

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add search-section-titles and empty-state classes
# unfilledTab
content = content.replace('<div class="tab-pane fade show active" id="unfilledTab" role="tabpanel">', 
                          '<div class="tab-pane fade show active" id="unfilledTab" role="tabpanel">\n                <h4 class="fw-bold mb-3 search-section-title d-none">Активные отчеты</h4>')
# overdueTab
content = content.replace('<div class="tab-pane fade" id="overdueTab" role="tabpanel">', 
                          '<div class="tab-pane fade" id="overdueTab" role="tabpanel">\n                <h4 class="fw-bold mb-3 search-section-title d-none text-danger">Просроченные</h4>')
# filledTab
content = content.replace('<div class="tab-pane fade" id="filledTab" role="tabpanel">', 
                          '<div class="tab-pane fade" id="filledTab" role="tabpanel">\n                <h4 class="fw-bold mb-3 search-section-title d-none">Сданные отчеты</h4>')
# filesTab
content = content.replace('<div class="tab-pane fade" id="filesTab" role="tabpanel">', 
                          '<div class="tab-pane fade" id="filesTab" role="tabpanel">\n                <h4 class="fw-bold mb-3 search-section-title d-none">Прикрепленные файлы</h4>')

# empty-states
content = content.replace('<div class="col-12">\n                        <div class="text-center py-5 text-muted', 
                          '<div class="col-12 empty-state">\n                        <div class="text-center py-5 text-muted')
content = content.replace('<div class="col-12">\n                        <div class="text-center py-4 text-muted', 
                          '<div class="col-12 empty-state">\n                        <div class="text-center py-4 text-muted')


# 2. Replace the script block entirely
new_script = """
        <script>
            document.addEventListener("DOMContentLoaded", function () {
                const searchInput = document.getElementById('userReportSearch');
                const sortSelect = document.getElementById('userReportSort');
                const navTabs = document.getElementById('userTabs'); // from user_dashboard.html
                
                function applyFilterAndSort() {
                    if (!searchInput) return;
                    const query = searchInput.value.toLowerCase().trim();
                    const sortVal = sortSelect ? sortSelect.value : '';
                    
                    const sections = [
                        {id: 'unfilledContainer', paneId: 'unfilledTab'},
                        {id: 'overdueContainer', paneId: 'overdueTab'},
                        {id: 'filledContainer', paneId: 'filledTab'},
                        {id: 'filesContainer', paneId: 'filesTab'}
                    ];
                    
                    if (query.length > 0) {
                        if (navTabs) navTabs.style.display = 'none';
                        
                        sections.forEach(sec => {
                            const hasVisible = processContainer(sec.id, query, sortVal);
                            const pane = document.getElementById(sec.paneId);
                            if (pane) {
                                pane.classList.add('d-block', 'opacity-100');
                                const title = pane.querySelector('.search-section-title');
                                if (title) {
                                    if (hasVisible) {
                                        title.classList.remove('d-none');
                                    } else {
                                        title.classList.add('d-none');
                                    }
                                }
                                if (!hasVisible) {
                                    pane.style.display = 'none';
                                } else {
                                    pane.style.display = 'block';
                                }
                            }
                        });
                    } else {
                        if (navTabs) navTabs.style.display = '';
                        
                        sections.forEach(sec => {
                            processContainer(sec.id, '', sortVal);
                            const pane = document.getElementById(sec.paneId);
                            if (pane) {
                                pane.classList.remove('d-block', 'opacity-100');
                                pane.style.display = ''; // let bootstrap manage it
                                const title = pane.querySelector('.search-section-title');
                                if (title) title.classList.add('d-none');
                            }
                        });
                    }
                }
                
                function processContainer(containerId, query, sortVal) {
                    const container = document.getElementById(containerId);
                    if (!container) return false;
                    let items = Array.from(container.querySelectorAll('.user-report-item'));
                    let visibleCount = 0;
                    
                    items.forEach(item => {
                        const title = item.getAttribute('data-title') || '';
                        if (title.includes(query)) {
                            item.style.display = '';
                            visibleCount++;
                        } else {
                            item.style.display = 'none';
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
                
                if (searchInput) searchInput.addEventListener('input', applyFilterAndSort);
                if (sortSelect) sortSelect.addEventListener('change', applyFilterAndSort);
            });
        </script>
"""

# Replace the script chunk
script_pattern = r'<script>\s*document\.addEventListener\("DOMContentLoaded".*?}\);\s*</script>'
content = re.sub(script_pattern, new_script.strip(), content, flags=re.DOTALL)

with open('/home/copp-admin/copp-ras/app/templates/user_tabs/reports_tabs.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
