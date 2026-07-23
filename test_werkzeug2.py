from werkzeug.datastructures import FileStorage
from io import BytesIO

f = BytesIO(b'SQLite format 3\0001234')
fs = FileStorage(stream=f, filename='test.db')
print("read:", fs.read(16))
fs.seek(0)
with open('out.db', 'wb') as dst:
    fs.save(dst)
print("out size:", open('out.db', 'rb').read())
