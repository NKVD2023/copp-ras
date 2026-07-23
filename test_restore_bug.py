import requests
import time
import threading
import os
import sqlite3

def start_app():
    os.system("source venv/bin/activate && python run.py > app_bug.log 2>&1")

# Clean state
shutil_cmd = "cp copp_backup_20260722_113402.db reports.db"
os.system(shutil_cmd)

t = threading.Thread(target=start_app, daemon=True)
t.start()
time.sleep(3)

session = requests.Session()
# Login
resp = session.post('http://127.0.0.1:5000/login', data={'username': 'admin', 'password': '123'})
print("Login status:", resp.status_code)

# 1. Create backup
resp = session.post('http://127.0.0.1:5000/admin/db/backup/create')
print("Create backup status:", resp.status_code)

# Get the created backup filename from the DB
c = sqlite3.connect('reports.db')
last_log = c.execute("SELECT details FROM action_logs WHERE action='Бэкап БД' ORDER BY timestamp DESC LIMIT 1").fetchone()[0]
backup_name = last_log.split()[-1]
print("Backup created:", backup_name)

# 2. Delete a report submission
# We will just use sqlite3 to delete a submission to simulate user deleting it, or use the app's route if it exists.
# The app has: POST /admin/reports/delete_submission/<int:submission_id>
# Let's get a submission ID
sub_id = c.execute("SELECT id FROM report_submissions LIMIT 1").fetchone()[0]
resp = session.post(f'http://127.0.0.1:5000/admin/reports/delete_submission/{sub_id}')
print(f"Delete submission {sub_id} status:", resp.status_code)

# 3. Restore the backup
resp = session.post(f'http://127.0.0.1:5000/admin/db/backup/restore/{backup_name}', headers={'X-User-Password': '123'})
print("Restore backup status:", resp.status_code)

# Check if submission is back
c = sqlite3.connect('reports.db')
sub_exists = c.execute(f"SELECT id FROM report_submissions WHERE id={sub_id}").fetchone()
print("Submission exists after restore:", sub_exists is not None)

