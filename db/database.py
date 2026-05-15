# db/database.py
# 数据库模块 — SQLite 初始化与增删查操作封装

import sqlite3
import os
from utils.logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'mail.db')


def get_conn() -> sqlite3.Connection:
    """获取数据库连接，自动开启 WAL 模式提升并发性能"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # 让查询结果支持按列名访问
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


# ------------------------------------------------------------------ #
#  初始化
# ------------------------------------------------------------------ #

def init_db():
    """初始化数据库，创建所有表（若已存在则跳过）"""
    conn = get_conn()
    cursor = conn.cursor()

    # 收件箱
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

    # 已发送
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

    # 账户
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

def insert_inbox(mail: dict) -> bool:
    """
    存入一封收到的邮件

    参数 mail 为 mail_parser.parse_mail() 的返回字典，包含：
        from_addr, subject, body, date, raw
    返回 True 表示插入成功，False 表示已存在（去重跳过）
    """
    # 用 from_addr + subject + date 简单去重，避免重复收取
    conn = get_conn()
    try:
        uid = mail.get('_uid', '')
        # 有 UID 时按 UID 去重，无 UID 时按 from+subject+date 去重
        if uid:
            exists = conn.execute(
                'SELECT id FROM inbox WHERE uid = ?', (uid,)
            ).fetchone()
        else:
            exists = conn.execute(
                'SELECT id FROM inbox WHERE from_addr=? AND subject=? AND receive_time=?',
                (mail.get('from_addr',''), mail.get('subject',''), mail.get('date',''))
            ).fetchone()

        if exists:
            logger.debug(f'[DB] 邮件已存在，跳过: {mail.get("subject")}')
            return False

        conn.execute('''
            INSERT INTO inbox (from_addr, subject, body, receive_time, is_read, raw_data, uid)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        ''', (
            mail.get('from_addr', ''),
            mail.get('subject', ''),
            mail.get('body', ''),
            mail.get('date', ''),
            mail.get('raw', ''),
            uid
        ))
        conn.commit()
        logger.info(f'[DB] 存入收件箱: {mail.get("subject")}')
        return True
    finally:
        conn.close()


def get_inbox() -> list:
    """
    查询收件箱所有邮件，按时间倒序排列（最新的在最前）

    返回 list of dict，每项包含：
        id, from_addr, subject, body, receive_time, is_read
    """
    conn = get_conn()
    try:
        rows = conn.execute('''
            SELECT id, from_addr, subject, body, receive_time, is_read, raw_data
            FROM inbox
            ORDER BY id DESC
        ''').fetchall()
        return [dict(row) for row in rows]
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
        conn.execute('''
            INSERT INTO sent_mails (to_addr, subject, body, status)
            VALUES (?, ?, ?, ?)
        ''', (
            mail.get('to_addr', ''),
            mail.get('subject', ''),
            mail.get('body', ''),
            mail.get('status', 'success')
        ))
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
        rows = conn.execute('''
            SELECT id, to_addr, subject, body, send_time, status
            FROM sent_mails
            ORDER BY id DESC
        ''').fetchall()
        # 已发送列表用 from_addr 字段显示收件人，统一格式给 GUI 使用
        result = []
        for row in rows:
            d = dict(row)
            d['from_addr']    = d['to_addr']    # GUI 列表统一读 from_addr
            d['receive_time'] = d['send_time']  # GUI 列表统一读 receive_time
            d['is_read']      = 1               # 已发送默认已读
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
        conn.execute('''
            INSERT INTO accounts (email, password, smtp_host, smtp_port,
                                  pop3_host, pop3_port)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                password  = excluded.password,
                smtp_host = excluded.smtp_host,
                smtp_port = excluded.smtp_port,
                pop3_host = excluded.pop3_host,
                pop3_port = excluded.pop3_port
        ''', (
            account.get('email', ''),
            account.get('password', ''),
            account.get('smtp_host', 'smtp.qq.com'),
            account.get('smtp_port', 465),
            account.get('pop3_host', 'pop.qq.com'),
            account.get('pop3_port', 995)
        ))
        conn.commit()
        logger.info(f'[DB] 账户已保存: {account.get("email")}')
    finally:
        conn.close()


def get_account(email: str) -> dict:
    """
    查询指定邮箱的账户信息，不存在则返回 None
    """
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