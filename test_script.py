import re

with open("app/templates/user_tabs/reports_tabs.html", "r") as f:
    content = f.read()

# I need to add data-original-container to each user-report-item
content = content.replace('class="col-md-6 col-lg-4 col-xl-3 user-report-item" data-title="', 'class="col-md-6 col-lg-4 col-xl-3 user-report-item" data-original-container="unfilledContainer" data-title="')
# Wait, this would replace all of them with unfilledContainer! I should do it in JS on load, or dynamically!
