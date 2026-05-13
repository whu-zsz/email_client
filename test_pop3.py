# test_pop3.py
# 放在项目根目录 email_client/ 下，用于独立测试 POP3 收信
# 运行方式: python test_pop3.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.pop3_client import POP3Client
from core.mail_parser import parse_mail

# ============================================================
# 填入你的真实信息后运行
# ============================================================
MY_EMAIL  = '2322731680@qq.com'   # 收件邮箱
MY_PASSWD = 'rqnrgjxseogdeaaj'         # QQ邮箱授权码（非登录密码）
# ============================================================


def test_connect():
    """测试1：连接与登录"""
    print('=== 测试1：连接与登录 ===')
    client = POP3Client(host='pop.qq.com', port=995)
    client.connect()
    client.login(MY_EMAIL, MY_PASSWD)
    count, size = client.stat()
    print(f'  收件箱共 {count} 封邮件，总大小 {size} 字节')
    client.quit()
    print('✅ 测试1 通过\n')


def test_list():
    """测试2：获取邮件列表"""
    print('=== 测试2：获取邮件列表 ===')
    client = POP3Client(host='pop.qq.com', port=995)
    client.connect()
    client.login(MY_EMAIL, MY_PASSWD)
    mail_list = client.list_mails()
    print(f'  邮件列表（最多显示前5封）：')
    for idx, size in list(mail_list.items())[-5:]:
        print(f'    #{idx}  {size} 字节')
    client.quit()
    print('✅ 测试2 通过\n')


def test_retrieve_and_parse():
    """测试3：下载并解析最新一封邮件"""
    print('=== 测试3：下载并解析最新邮件 ===')
    client = POP3Client(host='pop.qq.com', port=995)
    client.connect()
    client.login(MY_EMAIL, MY_PASSWD)

    mail_list = client.list_mails()
    if not mail_list:
        print('  收件箱为空，跳过此测试')
        client.quit()
        return

    # 取编号最大（最新）的一封
    latest_idx = max(mail_list.keys())
    print(f'  下载第 #{latest_idx} 封邮件...')

    raw = client.retrieve_mail(latest_idx)
    client.quit()

    # 解析
    parsed = parse_mail(raw)
    print(f'  发件人 : {parsed["from"]}')
    print(f'  主  题 : {parsed["subject"]}')
    print(f'  日  期 : {parsed["date"]}')
    print(f'  正文预览: {parsed["body"][:100]}...')
    print(f'  附  件 : {len(parsed["attachments"])} 个')
    print('✅ 测试3 通过\n')


def test_fetch_all():
    """测试4：使用简便接口一次收取多封邮件"""
    print('=== 测试4：批量收取最新5封邮件 ===')
    client = POP3Client(host='pop.qq.com', port=995)
    mails = client.fetch_all(MY_EMAIL, MY_PASSWD, max_count=5)
    for i, m in enumerate(mails, 1):
        print(f'  [{i}] {m["date"]}  {m["from_addr"]}  {m["subject"]}')
    print(f'✅ 测试4 通过，共收取 {len(mails)} 封\n')


def test_top_headers():
    """测试5：只下载邮件头部（快速预览，不下载正文）"""
    print('=== 测试5：快速预览邮件头部 ===')
    client = POP3Client(host='pop.qq.com', port=995)
    client.connect()
    client.login(MY_EMAIL, MY_PASSWD)

    mail_list = client.list_mails()
    if not mail_list:
        print('  收件箱为空，跳过')
        client.quit()
        return

    latest_idx = max(mail_list.keys())
    header_raw = client.top(latest_idx, lines=0)
    client.quit()

    # 只解析头部
    parsed = parse_mail(header_raw)
    print(f'  发件人: {parsed["from"]}')
    print(f'  主  题: {parsed["subject"]}')
    print(f'  日  期: {parsed["date"]}')
    print('✅ 测试5 通过\n')


if __name__ == '__main__':
    test_connect()
    test_list()
    test_retrieve_and_parse()
    test_fetch_all()
    test_top_headers()
    print('🎉 全部测试完成！POP3 收信模块工作正常。')
