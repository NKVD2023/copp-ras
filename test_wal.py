import sqlite3
import shutil
import os

c = sqlite3.connect('wal_test.db')
c.execute('PRAGMA journal_mode=WAL;')
c.execute('CREATE TABLE t (id INT);')
c.execute('INSERT INTO t VALUES (1);')
c.commit()

shutil.copy2('wal_test.db', 'wal_copy.db')
c2 = sqlite3.connect('wal_copy.db')
print("Journal mode of copy:", c2.execute('PRAGMA journal_mode;').fetchone())
print("Data in copy:", c2.execute('SELECT * FROM t').fetchall())
