import requests
import time
import threading
import os

# Start app in background
def start_app():
    os.system("source venv/bin/activate && python run.py > app.log 2>&1")

t = threading.Thread(target=start_app, daemon=True)
t.start()
time.sleep(3)

session = requests.Session()
# We need to login as admin to the app
resp = session.post('http://127.0.0.1:5000/login', data={'username': 'admin', 'password': '123'})
print("Login status:", resp.status_code)

# Now upload the file
with open('copp_backup_20260722_113402.db', 'rb') as f:
    files = {'backup_file': ('copp_backup.db', f, 'application/octet-stream')}
    resp2 = session.post('http://127.0.0.1:5000/admin/db/backup/upload', files=files, allow_redirects=True)
    print("Upload status:", resp2.status_code)

# Check dashboard data
resp3 = session.get('http://127.0.0.1:5000/admin/')
if 'saki_tech' in resp3.text:
    print("Dashboard shows prod users!")
else:
    print("Dashboard DOES NOT show prod users!")
