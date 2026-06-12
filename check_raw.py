import os
import sqlite3

DB_PATH = os.path.join('data', 'mail.db')
conn = sqlite3.connect(DB_PATH)
row = conn.execute(
    'SELECT id, subject, raw_data, raw_eml FROM inbox ORDER BY id DESC LIMIT 1'
).fetchone()

if not row:
    print('收件箱为空')
else:
    row_id, subject, raw_data, raw_eml = row
    print(f'id={row_id}, subject={repr(subject)}')
    print(f'raw_data 长度: {len(raw_data or "")}')
    print(f'raw_eml 长度: {len(raw_eml or b"")}')

    if raw_data:
        print('--- raw_data 前300字符 ---')
        print(repr(raw_data[:300]))
    if raw_eml:
        print('--- raw_eml 前120字节 ---')
        print(repr(raw_eml[:120]))

    if raw_data and raw_eml:
        try:
            same_bytes = raw_data.encode('latin-1', errors='strict') == raw_eml
        except UnicodeEncodeError:
            same_bytes = False
        print(f'raw_data latin-1 回转后是否等于 raw_eml: {same_bytes}')

conn.close()
