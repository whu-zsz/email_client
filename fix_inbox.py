# fix_inbox.py
# 放在项目根目录运行：python fix_inbox.py
# 作用：优先使用 raw_eml 重新解析数据库里所有邮件，修复主题、正文与 MIME 资源

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))

from core.mail_parser import parse_mail
from db.database import get_conn, update_inbox_content

DB_PATH = os.path.join('data', 'mail.db')


def _choose_raw_source(raw_eml, raw_data):
    if raw_eml:
        return raw_eml, 'raw_eml'
    if raw_data:
        return raw_data, 'raw_data'
    return None, None


def main():
    conn = get_conn()
    rows = conn.execute(
        'SELECT id, raw_eml, raw_data FROM inbox ORDER BY id ASC'
    ).fetchall()
    conn.close()

    print(f'共 {len(rows)} 封邮件，开始重新解析...')

    repaired_from_eml = 0
    repaired_from_text = 0
    skipped = 0
    failed = 0

    for row in rows:
        row_id = row['id'] if isinstance(row, sqlite3.Row) else row[0]
        raw_eml = row['raw_eml'] if isinstance(row, sqlite3.Row) else row[1]
        raw_data = row['raw_data'] if isinstance(row, sqlite3.Row) else row[2]

        raw_source, source_name = _choose_raw_source(raw_eml, raw_data)
        if raw_source is None:
            print(f'  id={row_id}: 无原始邮件可用于修复，跳过')
            skipped += 1
            continue

        try:
            parsed = parse_mail(raw_source)
            update_inbox_content(row_id, parsed)

            subject = (parsed.get('subject', '') or '')[:40]
            body = (parsed.get('text_body', parsed.get('body', '')) or '')[:40]
            print(f'  id={row_id}: [{source_name}] subject={repr(subject)} body={repr(body)}')

            if source_name == 'raw_eml':
                repaired_from_eml += 1
            else:
                repaired_from_text += 1
        except Exception as e:
            print(f'  id={row_id}: 修复失败 {e}')
            failed += 1

    print('\n修复完成：')
    print(f'  由 raw_eml 修复: {repaired_from_eml}')
    print(f'  由 raw_data 兜底修复: {repaired_from_text}')
    print(f'  无原始源跳过: {skipped}')
    print(f'  解析失败: {failed}')
    print(f'\n数据库位置: {DB_PATH}')


if __name__ == '__main__':
    main()
