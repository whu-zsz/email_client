# test_smtp.py
# 放在项目根目录 email_client/ 下，用于独立测试 SMTP 发送
# 运行方式: python test_smtp.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.smtp_client import SMTPClient

# ============================================================
# 填入你的真实信息后运行
# ============================================================
MY_EMAIL  = '2322731680@qq.com'   # 发件人 填自己的邮箱
MY_PASSWD = 'rqnrgjxseogdeaaj'         # QQ邮箱授权码（非登录密码）
TO_EMAIL  = '2322731680@qq.com' # 收件人（可填自己验证）
# ============================================================

def test_simple():
    """测试1：发送一封简单纯文本邮件"""
    print('=== 测试1：发送纯文本邮件 ===')
    client = SMTPClient(host='smtp.qq.com', port=465)
    client.send(
        username=MY_EMAIL,
        password=MY_PASSWD,
        to_addr=TO_EMAIL,
        subject='【测试】SMTP发送测试',
        body='你好，这是来自课设邮件客户端的测试邮件！\n\n发送成功说明 SMTP 模块工作正常。'
    )
    print('✅ 测试1 通过\n')


def test_chinese():
    """测试2：中文主题和正文"""
    print('=== 测试2：中文主题与正文 ===')
    client = SMTPClient(host='smtp.qq.com', port=465)
    client.send(
        username=MY_EMAIL,
        password=MY_PASSWD,
        to_addr=TO_EMAIL,
        subject='中文主题测试：你好世界',
        body='正文也是中文：\n\n计算机网络课设邮件系统\nSMTP 协议测试成功！'
    )
    print('✅ 测试2 通过\n')


def test_attachment():
    """测试3：带附件发送（需在项目目录下有 test_file.txt）"""
    print('=== 测试3：带附件发送 ===')

    # 自动创建一个测试附件
    with open('test_file.txt', 'w', encoding='utf-8') as f:
        f.write('这是测试附件的内容。\nSMTP 附件测试。\n')

    client = SMTPClient(host='smtp.qq.com', port=465)
    client.send(
        username=MY_EMAIL,
        password=MY_PASSWD,
        to_addr=TO_EMAIL,
        subject='【测试】带附件的邮件',
        body='请查收附件。',
        attachments=['test_file.txt']
    )
    print('✅ 测试3 通过\n')


if __name__ == '__main__':
    test_simple()
    test_chinese()
    test_attachment()
    print('🎉 全部测试完成，请登录收件人邮箱确认收到邮件。')
