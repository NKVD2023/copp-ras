from werkzeug.datastructures import FileStorage
from io import BytesIO
import os

with open('/home/copp-admin/copp-ras/copp_backup_20260722_113402.db', 'rb') as f:
    data = f.read()

f_stream = BytesIO(data)
fs = FileStorage(stream=f_stream, filename='test.db')
print("Header read:", fs.read(16))
fs.seek(0)
fs.save('out_test.db')
print("out size:", os.path.getsize('out_test.db'))
