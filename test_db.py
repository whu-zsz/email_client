# test_db.py
# 放在项目根目录 email_client/ 下，用于独立测试数据库模块
# 运行方式: python test_db.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db.database import (
    init_db, insert_inbox, get_inbox, mark_as_read,
    delete_mail, insert_sent, get_sent,
    save_account, get_account
)


def test_init():
    print('=== 测试1：初始化数据库 ===')
    init_db()
    print('✅ 测试1 通过\n')


def test_inbox():
    print('=== 测试2：收件箱增删查 ===')

    # 插入两封测试邮件
    mail1 = {
        'from_addr': 'alice@qq.com',
        'subject':   '你好，这是测试邮件1',
        'body':      '正文内容一',
        'date':      '2026-05-14 10:00',
        'raw':       ''
    }
    mail2 = {
        'from_addr': 'bob@163.com',
        'subject':   '测试邮件2',
        'body':      '正文内容二',
        'date':      '2026-05-14 11:00',
        'raw':       ''
    }
    insert_inbox(mail1)
    insert_inbox(mail2)

    # 再次插入 mail1，应被去重跳过
    result = insert_inbox(mail1)
    assert result == False, '去重失败'

    # 查询
    mails = get_inbox()
    assert len(mails) >= 2, '查询收件箱失败'
    print(f'  收件箱共 {len(mails)} 封邮件：')
    for m in mails[:3]:
        print(f'    [{m["id"]}] {m["from_addr"]}  {m["subject"]}  已读:{m["is_read"]}')

    # 标记已读
    first_id = mails[0]['id']
    mark_as_read(first_id)
    updated = get_inbox()
    target = next(m for m in updated if m['id'] == first_id)
    assert target['is_read'] == 1, '标记已读失败'
    print(f'  标记 id={first_id} 已读 ✓')

    # 删除
    delete_mail(first_id, folder='inbox')
    after_delete = get_inbox()
    assert all(m['id'] != first_id for m in after_delete), '删除失败'
    print(f'  删除 id={first_id} ✓')

    print('✅ 测试2 通过\n')


def test_sent():
    print('=== 测试3：已发送增删查 ===')

    insert_sent({
        'to_addr': 'charlie@qq.com',
        'subject': '发送测试主题',
        'body':    '发送正文',
        'status':  'success'
    })

    mails = get_sent()
    assert len(mails) >= 1, '查询已发送失败'
    print(f'  已发送共 {len(mails)} 封：')
    for m in mails[:3]:
        print(f'    [{m["id"]}] → {m["to_addr"]}  {m["subject"]}')

    # 删除
    first_id = mails[0]['id']
    delete_mail(first_id, folder='sent')
    after = get_sent()
    assert all(m['id'] != first_id for m in after), '删除已发送失败'
    print(f'  删除 id={first_id} ✓')

    print('✅ 测试3 通过\n')


def test_account():
    print('=== 测试4：账户保存与查询 ===')

    save_account({
        'email':     'test@qq.com',
        'password':  'testpassword',
        'smtp_host': 'smtp.qq.com',
        'smtp_port': 465,
        'pop3_host': 'pop.qq.com',
        'pop3_port': 995
    })

    acc = get_account('test@qq.com')
    assert acc is not None, '账户查询失败'
    assert acc['email'] == 'test@qq.com', '账户邮箱不匹配'
    print(f'  账户: {acc["email"]}  smtp: {acc["smtp_host"]}:{acc["smtp_port"]}')

    # 更新密码（ON CONFLICT 覆盖）
    save_account({
        'email':     'test@qq.com',
        'password':  'newpassword',
        'smtp_host': 'smtp.qq.com',
        'smtp_port': 465,
        'pop3_host': 'pop.qq.com',
        'pop3_port': 995
    })
    acc2 = get_account('test@qq.com')
    assert acc2['password'] == 'newpassword', '账户更新失败'
    print('  账户更新覆盖 ✓')

    print('✅ 测试4 通过\n')


if __name__ == '__main__':
    # 使用测试专用数据库，不污染正式数据
    import db.database as db_module
    db_module.DB_PATH = os.path.join(
        os.path.dirname(__file__), 'data', 'test_mail.db'
    )
    # 清空旧测试数据库
    if os.path.exists(db_module.DB_PATH):
        os.remove(db_module.DB_PATH)

    test_init()
    test_inbox()
    test_sent()
    test_account()

    print('🎉 全部测试通过！数据库模块工作正常。')

    # 清理测试数据库
    if os.path.exists(db_module.DB_PATH):
        os.remove(db_module.DB_PATH)
        print('（测试数据库已清理）')
