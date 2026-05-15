# db/database.py
# 数据库模块 — SQLite 初始化与增删查操作封装

import os
import sqlite3

from utils.logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'mail.db')



def get_conn() -> sqlite3.Connection:
    """获取数据库连接，自动开启 WAL 模式提升并发性能"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn



def _get_columns(conn: sqlite3.Connection, table: str) -> set:
    """读取指定表的现有列集合"""
    rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
    return {row['name'] for row in rows}



def _ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str):
    """若列不存在则执行迁移"""
    if name in _get_columns(conn, table):
        return
    conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')
    logger.info(f'[DB] 已迁移列: {table}.{name}')



# ------------------------------------------------------------------ #
#  初始化
# ------------------------------------------------------------------ #


def init_db():
    """初始化数据库，创建所有表（若已存在则跳过）"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inbox (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_addr    TEXT    NOT NULL,
            subject      TEXT    DEFAULT '',
            body         TEXT    DEFAULT '',
            receive_time TEXT    DEFAULT (datetime('now', 'localtime')),
            is_read      INTEGER DEFAULT 0,
            raw_data     TEXT    DEFAULT '',
            uid          TEXT    DEFAULT ''
        )
    ''')

    _ensure_column(conn, 'inbox', 'text_body', "TEXT DEFAULT ''")
    _ensure_column(conn, 'inbox', 'html_body', "TEXT DEFAULT ''")
    _ensure_column(conn, 'inbox', 'raw_eml', 'BLOB')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mail_parts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            mail_id         INTEGER NOT NULL,
            filename        TEXT    DEFAULT '',
            content_type    TEXT    DEFAULT '',
            content_id      TEXT    DEFAULT '',
            disposition     TEXT    DEFAULT '',
            is_inline       INTEGER DEFAULT 0,
            data            BLOB,
            size            INTEGER DEFAULT 0,
            FOREIGN KEY(mail_id) REFERENCES inbox(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_mails (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            to_addr   TEXT    NOT NULL,
            subject   TEXT    DEFAULT '',
            body      TEXT    DEFAULT '',
            send_time TEXT    DEFAULT (datetime('now', 'localtime')),
            status    TEXT    DEFAULT 'success'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            email     TEXT    UNIQUE NOT NULL,
            password  TEXT    NOT NULL,
            smtp_host TEXT    DEFAULT 'smtp.qq.com',
            smtp_port INTEGER DEFAULT 465,
            pop3_host TEXT    DEFAULT 'pop.qq.com',
            pop3_port INTEGER DEFAULT 995
        )
    ''')

    conn.commit()
    conn.close()
    logger.info('[DB] 数据库初始化完成')



# ------------------------------------------------------------------ #
#  收件箱操作
# ------------------------------------------------------------------ #


def _save_mail_parts(conn: sqlite3.Connection, mail_id: int, parts: list):
    """保存附件或内嵌资源"""
    if not parts:
        return
    conn.executemany(
        '''
        INSERT INTO mail_parts (mail_id, filename, content_type, content_id,
                                disposition, is_inline, data, size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        [
            (
                mail_id,
                part.get('filename', ''),
                part.get('content_type', ''),
                part.get('content_id', ''),
                part.get('disposition', ''),
                1 if part.get('is_inline') else 0,
                part.get('data', b''),
                part.get('size', len(part.get('data', b''))),
            )
            for part in parts
        ],
    )



def insert_inbox(mail: dict) -> bool:
    """
    存入一封收到的邮件

    参数 mail 为 mail_parser.parse_mail() 的返回字典，包含：
        from_addr, subject, body/text_body/html_body, date, raw, raw_bytes
    返回 True 表示插入成功，False 表示已存在（去重跳过）
    """
    conn = get_conn()
    try:
        uid = mail.get('_uid', '')
        if uid:
            exists = conn.execute(
                'SELECT id FROM inbox WHERE uid = ?', (uid,)
            ).fetchone()
        else:
            exists = conn.execute(
                'SELECT id FROM inbox WHERE from_addr=? AND subject=? AND receive_time=?',
                (mail.get('from_addr', ''), mail.get('subject', ''), mail.get('date', '')),
            ).fetchone()

        if exists:
            logger.debug(f'[DB] 邮件已存在，跳过: {mail.get("subject")}')
            return False

        cursor = conn.execute(
            '''
            INSERT INTO inbox (
                from_addr, subject, body, text_body, html_body,
                receive_time, is_read, raw_data, raw_eml, uid
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            ''',
            (
                mail.get('from_addr', ''),
                mail.get('subject', ''),
                mail.get('body', ''),
                mail.get('text_body', mail.get('body', '')),
                mail.get('html_body', ''),
                mail.get('date', ''),
                mail.get('raw', ''),
                mail.get('raw_bytes', b''),
                uid,
            ),
        )
        mail_id = cursor.lastrowid
        _save_mail_parts(conn, mail_id, mail.get('attachments', []))
        _save_mail_parts(conn, mail_id, mail.get('inline_parts', []))
        conn.commit()
        logger.info(f'[DB] 存入收件箱: {mail.get("subject")}')
        return True
    finally:
        conn.close()



def get_inbox() -> list:
    """
    查询收件箱所有邮件，按时间倒序排列（最新的在最前）

    返回 list of dict，每项包含：
        id, from_addr, subject, body, text_body, html_body, receive_time, is_read
    """
    conn = get_conn()
    try:
        rows = conn.execute(
            '''
            SELECT id, from_addr, subject, body, text_body, html_body,
                   receive_time, is_read, raw_data
            FROM inbox
            ORDER BY id DESC
            '''
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()



def get_mail_parts(mail_id: int) -> list:
    """查询指定邮件的附件与内嵌资源"""
    conn = get_conn()
    try:
        rows = conn.execute(
            '''
            SELECT id, mail_id, filename, content_type, content_id,
                   disposition, is_inline, data, size
            FROM mail_parts
            WHERE mail_id = ?
            ORDER BY id ASC
            ''',
            (mail_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['is_inline'] = bool(item.get('is_inline'))
            result.append(item)
        return result
    finally:
        conn.close()



def update_inbox_content(mail_id: int, parsed: dict):
    """按最新解析结果回写正文和 MIME 资源"""
    conn = get_conn()
    try:
        conn.execute(
            '''
            UPDATE inbox
            SET body = ?, text_body = ?, html_body = ?, raw_data = ?, raw_eml = ?
            WHERE id = ?
            ''',
            (
                parsed.get('body', ''),
                parsed.get('text_body', parsed.get('body', '')),
                parsed.get('html_body', ''),
                parsed.get('raw', ''),
                parsed.get('raw_bytes', b''),
                mail_id,
            ),
        )
        conn.execute('DELETE FROM mail_parts WHERE mail_id = ?', (mail_id,))
        _save_mail_parts(conn, mail_id, parsed.get('attachments', []))
        _save_mail_parts(conn, mail_id, parsed.get('inline_parts', []))
        conn.commit()
        logger.info(f'[DB] 已更新邮件内容: id={mail_id}')
    finally:
        conn.close()



def get_all_uids() -> set:
    """返回数据库中所有已存邮件的 UID 集合，用于增量收信去重"""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT uid FROM inbox WHERE uid != ''").fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()



def mark_as_read(mail_id: int):
    """标记指定邮件为已读"""
    conn = get_conn()
    try:
        conn.execute('UPDATE inbox SET is_read = 1 WHERE id = ?', (mail_id,))
        conn.commit()
        logger.debug(f'[DB] 标记已读: id={mail_id}')
    finally:
        conn.close()



def delete_mail(mail_id: int, folder: str = 'inbox'):
    """
    删除指定邮件

    参数:
        mail_id : 邮件 id
        folder  : 'inbox' 或 'sent'，默认收件箱
    """
    table = 'inbox' if folder == 'inbox' else 'sent_mails'
    conn = get_conn()
    try:
        if folder == 'inbox':
            conn.execute('DELETE FROM mail_parts WHERE mail_id = ?', (mail_id,))
        conn.execute(f'DELETE FROM {table} WHERE id = ?', (mail_id,))
        conn.commit()
        logger.info(f'[DB] 删除邮件: {table} id={mail_id}')
    finally:
        conn.close()



# ------------------------------------------------------------------ #
#  已发送操作
# ------------------------------------------------------------------ #


def insert_sent(mail: dict):
    """
    存入一封已发送的邮件

    参数 mail 字典包含：
        to_addr, subject, body, status（可选，默认 'success'）
    """
    conn = get_conn()
    try:
        conn.execute(
            '''
            INSERT INTO sent_mails (to_addr, subject, body, status)
            VALUES (?, ?, ?, ?)
            ''',
            (
                mail.get('to_addr', ''),
                mail.get('subject', ''),
                mail.get('body', ''),
                mail.get('status', 'success'),
            ),
        )
        conn.commit()
        logger.info(f'[DB] 存入已发送: {mail.get("subject")}')
    finally:
        conn.close()



def get_sent() -> list:
    """
    查询已发送所有邮件，按时间倒序排列

    返回 list of dict，每项包含：
        id, to_addr, subject, body, send_time, status
    """
    conn = get_conn()
    try:
        rows = conn.execute(
            '''
            SELECT id, to_addr, subject, body, send_time, status
            FROM sent_mails
            ORDER BY id DESC
            '''
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['from_addr'] = d['to_addr']
            d['receive_time'] = d['send_time']
            d['is_read'] = 1
            d['text_body'] = d.get('body', '')
            d['html_body'] = ''
            result.append(d)
        return result
    finally:
        conn.close()



# ------------------------------------------------------------------ #
#  账户操作
# ------------------------------------------------------------------ #


def save_account(account: dict):
    """
    保存或更新账户信息（以 email 为唯一键）

    参数 account 字典包含：
        email, password, smtp_host, smtp_port, pop3_host, pop3_port
    """
    conn = get_conn()
    try:
        conn.execute(
            '''
            INSERT INTO accounts (email, password, smtp_host, smtp_port,
                                  pop3_host, pop3_port)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                password  = excluded.password,
                smtp_host = excluded.smtp_host,
                smtp_port = excluded.smtp_port,
                pop3_host = excluded.pop3_host,
                pop3_port = excluded.pop3_port
            ''',
            (
                account.get('email', ''),
                account.get('password', ''),
                account.get('smtp_host', 'smtp.qq.com'),
                account.get('smtp_port', 465),
                account.get('pop3_host', 'pop.qq.com'),
                account.get('pop3_port', 995),
            ),
        )
        conn.commit()
        logger.info(f'[DB] 账户已保存: {account.get("email")}')
    finally:
        conn.close()



def get_account(email: str) -> dict:
    """查询指定邮箱的账户信息，不存在则返回 None"""
    conn = get_conn()
    try:
        row = conn.execute(
            'SELECT * FROM accounts WHERE email = ?', (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



def get_all_accounts() -> list:
    """查询所有已保存的账户"""
    conn = get_conn()
    try:
        rows = conn.execute('SELECT * FROM accounts').fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
