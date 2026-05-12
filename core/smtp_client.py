# core/smtp_client.py
# 成员A负责实现

class SMTPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        pass  # TODO: 成员A实现

    def auth_login(self, username, password):
        pass  # TODO: 成员A实现

    def send_mail(self, from_addr, to_addr, subject, body, attachments=None):
        pass  # TODO: 成员A实现

    def quit(self):
        pass  # TODO: 成员A实现