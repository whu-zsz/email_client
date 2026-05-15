# check_all.py — 放项目根目录运行：python check_all.py
import sqlite3, os

DB_PATH = os.path.join('data', 'mail.db')
conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, subject, from_addr, body, raw_data FROM inbox").fetchall()

for row in rows:
    id_, subject, from_addr, body, raw_data = row
    print(f"\n{'='*60}")
    print(f"id={id_}  subject={repr(subject)}  from={repr(from_addr)}")
    print(f"--- body 前100字符 ---")
    print(repr((body or '')[:100]))
    print(f"--- raw_data 前300字符 ---")
    print(repr((raw_data or '')[:300]))

conn.close()
