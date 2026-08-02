import sqlite3

conn = sqlite3.connect("file:.source_catalog/catalog.sqlite3?mode=ro", uri=True)
print("quick_check=", conn.execute("PRAGMA quick_check").fetchone()[0])
fk = conn.execute("PRAGMA foreign_key_check").fetchall()
print("fk_rows=", len(fk))
conn.close()
