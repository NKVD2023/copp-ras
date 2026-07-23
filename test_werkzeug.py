from werkzeug.datastructures import FileStorage
import os

with open('test.db', 'wb') as f:
    f.write(b'12345678901234567890')

with open('test.db', 'rb') as f:
    fs = FileStorage(f)
    print("Header:", fs.read(16))
    fs.seek(0)
    fs.save('out.db')

print("Out size:", os.path.getsize('out.db'))
