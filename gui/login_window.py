# gui/login_window.py
import tkinter as tk

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title('邮件客户端 - 登录')
        self.root.geometry('400x300')
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root, text='邮箱账号：').pack(pady=5)
        self.email_entry = tk.Entry(self.root, width=30)
        self.email_entry.pack()

        tk.Label(self.root, text='授权码：').pack(pady=5)
        self.pwd_entry = tk.Entry(self.root, width=30, show='*')
        self.pwd_entry.pack()

        tk.Button(self.root, text='登 录', width=15,
                  command=self.on_login).pack(pady=20)

    def on_login(self):
        email = self.email_entry.get()
        pwd   = self.pwd_entry.get()
        print(f'[登录] {email}')
        # TODO: 成员C完善，调用成员D的账户管理