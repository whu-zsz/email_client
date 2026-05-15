# fix_inbox.py
# 放在项目根目录运行：python fix_inbox.py
# 作用：用最新的 mail_parser 重新解析数据库里所有邮件的 raw_data，修复 body/subject/from_addr

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
DB_PATH = os.path.join('data', 'mail.db')

from core.mail_parser import parse_mail

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, raw_data FROM inbox").fetchall()

print(f"共 {len(rows)} 封邮件，开始重新解析...")

fixed = 0
for row_id, raw_data in rows:
    if not raw_data:
        print(f"  id={row_id}: raw_data 为空，跳过")
        continue
    try:
        parsed = parse_mail(raw_data)
        conn.execute(
            "UPDATE inbox SET subject=?, from_addr=?, body=? WHERE id=?",
            (
                parsed.get('subject', '') or '',
                parsed.get('from_addr', '') or '',
                parsed.get('body', '') or '',
                row_id
            )
        )
        print(f"  id={row_id}: subject={repr(parsed.get('subject',''))[:30]}  body={repr(parsed.get('body',''))[:30]}")
        fixed += 1
    except Exception as e:
        print(f"  id={row_id}: 解析失败 {e}")

conn.commit()
conn.close()
print(f"\n完成，共修复 {fixed} 封邮件，重启程序查看效果。")
