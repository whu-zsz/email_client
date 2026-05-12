# db/database.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'mail.db')

def get_conn():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """初始化数据库，创建表结构"""
    conn = get_conn()
    cursor = conn.cursor()

    # 收件箱
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inbox (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_addr    TEXT,
            subject      TEXT,
            body         TEXT,
            receive_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read      INTEGER  DEFAULT 0,
            raw_data     TEXT
        )
    ''')

    # 已发送
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_mails (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            to_addr   TEXT,
            subject   TEXT,
            body      TEXT,
            send_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            status    TEXT     DEFAULT 'success'
        )
    ''')

    # 账户
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            email    TEXT UNIQUE,
            password TEXT,
            smtp_host TEXT,
            smtp_port INTEGER,
            pop3_host TEXT,
            pop3_port INTEGER
        )
    ''')

    conn.commit()
    conn.close()
    print('[DB] 数据库初始化完成')