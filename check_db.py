import sqlite3
import os

DB_PATH = os.path.join('data', 'mail.db')
conn = sqlite3.connect(DB_PATH)

rows = conn.execute("SELECT id, subject, from_addr, length(raw_data) as raw_len, length(body) as body_len FROM inbox").fetchall()
print(f"{'id':>4} {'subject':20} {'from':25} {'raw_data长度':>12} {'body长度':>8}")
print("-" * 75)
for r in rows:
    print(f"{r[0]:>4} {str(r[1]):20} {str(r[2]):25} {r[3]:>12} {r[4]:>8}")

conn.close()