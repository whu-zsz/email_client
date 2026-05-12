# core/smtp_client.py
# 成员A负责实现 — SMTP 发送模块
# 使用原生 socket + ssl 实现，不依赖 smtplib

import socket
import ssl
import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders

from utils.logger import logger


class SMTPClient:
    def __init__(self, host='smtp.qq.com', port=465):
        self.host = host
        self.port = port
        self.sock = None

    # ------------------------------------------------------------------ #
    #  底层收发
    # ------------------------------------------------------------------ #

    def _send(self, cmd: str):
        """发送一条 SMTP 命令（自动追加 CRLF）"""
        raw = (cmd + '\r\n').encode('utf-8')
        self.sock.sendall(raw)
        logger.debug(f'>>> {cmd}')

    def _recv(self) -> str:
        """接收服务器一条完整响应（以 CRLF 结尾）"""
        data = b''
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if data.endswith(b'\r\n'):
                break
        resp = data.decode('utf-8', errors='ignore').strip()
        logger.debug(f'<<< {resp}')
        return resp

    # ------------------------------------------------------------------ #
    #  连接与断开
    # ------------------------------------------------------------------ #

    def connect(self):
        """建立 TCP + SSL 连接，读取服务器欢迎信息"""
        logger.info(f'[SMTP] 连接 {self.host}:{self.port}')
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10)
        context = ssl.create_default_context()
        self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)
        self.sock.connect((self.host, self.port))
        resp = self._recv()
        if not resp.startswith('220'):
            raise ConnectionError(f'SMTP 连接失败: {resp}')
        logger.info('[SMTP] 连接成功')

    def quit(self):
        """发送 QUIT 并关闭连接"""
        try:
            self._send('QUIT')
            self._recv()
        finally:
            if self.sock:
                self.sock.close()
                self.sock = None
        logger.info('[SMTP] 连接已关闭')

    # ------------------------------------------------------------------ #
    #  握手与认证
    # ------------------------------------------------------------------ #

    def ehlo(self):
        """发送 EHLO 握手"""
        self._send('EHLO localhost')
        resp = self._recv()
        if not resp.startswith('250'):
            raise Exception(f'EHLO 失败: {resp}')
        logger.info('[SMTP] EHLO 握手成功')

    def auth_login(self, username: str, password: str):
        """
        AUTH LOGIN 认证
        username: 完整邮箱地址，如 xxx@qq.com
        password: 授权码（不是登录密码）
        """
        self._send('AUTH LOGIN')
        self._recv()  # 334 VXNlcm5hbWU6 (Username:)

        self._send(base64.b64encode(username.encode()).decode())
        self._recv()  # 334 UGFzc3dvcmQ6 (Password:)

        self._send(base64.b64encode(password.encode()).decode())
        resp = self._recv()

        if not resp.startswith('235'):
            raise PermissionError(f'认证失败: {resp}\n请确认授权码是否正确')
        logger.info(f'[SMTP] 认证成功: {username}')

    # ------------------------------------------------------------------ #
    #  构造邮件
    # ------------------------------------------------------------------ #

    def _build_message(self,
                       from_addr: str,
                       to_addr: str,
                       subject: str,
                       body: str,
                       attachments: list = None) -> str:
        """
        构造 MIME 格式邮件内容
        返回符合 RFC 2822 的邮件字符串
        """
        msg = MIMEMultipart()
        msg['From']    = from_addr
        msg['To']      = to_addr
        msg['Subject'] = Header(subject, 'utf-8')  # 中文主题编码

        # 正文（UTF-8 纯文本）
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 附件（可选）
        if attachments:
            for filepath in attachments:
                if not os.path.isfile(filepath):
                    logger.warning(f'[SMTP] 附件不存在，已跳过: {filepath}')
                    continue
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(filepath)
                part.add_header('Content-Disposition',
                                f'attachment; filename="{filename}"')
                msg.attach(part)
                logger.info(f'[SMTP] 添加附件: {filename}')

        return msg.as_string()

    # ------------------------------------------------------------------ #
    #  发送邮件
    # ------------------------------------------------------------------ #

    def send_mail(self,
                  from_addr: str,
                  to_addr: str,
                  subject: str,
                  body: str,
                  attachments: list = None):
        """
        发送一封邮件

        参数:
            from_addr   : 发件人地址，如 'xxx@qq.com'
            to_addr     : 收件人地址，如 'yyy@example.com'
            subject     : 邮件主题（支持中文）
            body        : 邮件正文（支持中文）
            attachments : 附件文件路径列表，如 ['report.pdf']，可不填
        """
        # 1. MAIL FROM
        self._send(f'MAIL FROM:<{from_addr}>')
        resp = self._recv()
        if not resp.startswith('250'):
            raise Exception(f'MAIL FROM 失败: {resp}')

        # 2. RCPT TO
        self._send(f'RCPT TO:<{to_addr}>')
        resp = self._recv()
        if not resp.startswith('250'):
            raise Exception(f'RCPT TO 失败: {resp}')

        # 3. DATA
        self._send('DATA')
        resp = self._recv()
        if not resp.startswith('354'):
            raise Exception(f'DATA 失败: {resp}')

        # 4. 发送邮件内容，以单独一行 '.' 结束
        mail_content = self._build_message(
            from_addr, to_addr, subject, body, attachments
        )
        self.sock.sendall((mail_content + '\r\n.\r\n').encode('utf-8'))

        # 5. 确认发送成功
        resp = self._recv()
        if not resp.startswith('250'):
            raise Exception(f'邮件发送失败: {resp}')

        logger.info(f'[SMTP] 发送成功 → {to_addr} | 主题: {subject}')
        return True

    # ------------------------------------------------------------------ #
    #  一步完成：连接 → 认证 → 发送 → 断开
    # ------------------------------------------------------------------ #

    def send(self,
             username: str,
             password: str,
             to_addr: str,
             subject: str,
             body: str,
             attachments: list = None):
        """
        对外暴露的简便接口，自动完成完整发送流程。

        参数:
            username    : 发件人邮箱
            password    : 授权码
            to_addr     : 收件人邮箱
            subject     : 主题
            body        : 正文
            attachments : 附件路径列表（可选）

        用法示例:
            client = SMTPClient()
            client.send('me@qq.com', '授权码', 'you@example.com',
                        '测试', '你好！')
        """
        try:
            self.connect()
            self.ehlo()
            self.auth_login(username, password)
            self.send_mail(username, to_addr, subject, body, attachments)
        finally:
            self.quit()
