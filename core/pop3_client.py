# core/pop3_client.py
# 成员B负责实现

class POP3Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        pass  # TODO: 成员B实现

    def login(self, username, password):
        pass  # TODO: 成员B实现

    def list_mails(self):
        pass  # TODO: 成员B实现

    def retrieve_mail(self, index):
        pass  # TODO: 成员B实现

    def delete_mail(self, index):
        pass  # TODO: 成员B实现

    def quit(self):
        pass  # TODO: 成员B实现