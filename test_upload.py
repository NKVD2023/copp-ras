import requests
from io import BytesIO

with open('/home/copp-admin/copp-ras/copp_backup_20260722_113402.db', 'rb') as f:
    data = f.read()

print("Original size:", len(data))
