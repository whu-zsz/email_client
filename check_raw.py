import sqlite3, os

DB_PATH = os.path.join('data', 'mail.db')
conn = sqlite3.connect(DB_PATH)

# 取第1封邮件的 raw_data 前 500 字符
row = conn.execute("SELECT id, subject, raw_data FROM inbox WHERE id=1").fetchone()
print(f"id={row[0]}, subject={repr(row[1])}")
print("--- raw_data 前500字符 ---")
print(row[2][:500])
print("--- raw_data 后200字符 ---")
print(row[2][-200:])
conn.close()
