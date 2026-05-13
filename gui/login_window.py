# gui/login_window.py
# 成员C负责实现 — 登录窗口
# tkinter 实现，支持 QQ / 163 邮箱快速填充

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.ini')

# 预设邮箱服务器配置
SERVER_PRESETS = {
    'QQ邮箱':  {'smtp_host': 'smtp.qq.com',  'smtp_port': 465,
                'pop3_host': 'pop.qq.com',   'pop3_port': 995},
    '163邮箱': {'smtp_host': 'smtp.163.com', 'smtp_port': 465,
                'pop3_host': 'pop.163.com',  'pop3_port': 995},
    '自定义':  {'smtp_host': '', 'smtp_port': 465,
                'pop3_host': '', 'pop3_port': 995},
}


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title('邮件客户端')
        self.root.geometry('420x480')
        self.root.resizable(False, False)
        self.root.configure(bg='#f5f5f0')

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 420) // 2
        y = (self.root.winfo_screenheight() - 480) // 2
        self.root.geometry(f'420x480+{x}+{y}')

        self._build_ui()
        self._load_config()

    # ------------------------------------------------------------------ #
    #  界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        bg = '#f5f5f0'

        # 顶部标题区
        header = tk.Frame(self.root, bg='#2c2c2a', height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='📧 邮件客户端',
                 font=('Microsoft YaHei', 18, 'bold'),
                 fg='white', bg='#2c2c2a').pack(expand=True)

        # 主体表单区
        form = tk.Frame(self.root, bg=bg, padx=40)
        form.pack(fill=tk.BOTH, expand=True, pady=20)

        # 邮箱类型选择
        tk.Label(form, text='邮箱类型', font=('Microsoft YaHei', 10),
                 fg='#5f5e5a', bg=bg).pack(anchor='w', pady=(0, 4))
        self.server_var = tk.StringVar(value='QQ邮箱')
        server_cb = ttk.Combobox(form, textvariable=self.server_var,
                                 values=list(SERVER_PRESETS.keys()),
                                 state='readonly', font=('Microsoft YaHei', 11))
        server_cb.pack(fill=tk.X, ipady=4)
        server_cb.bind('<<ComboboxSelected>>', self._on_server_change)

        # 邮箱地址
        tk.Label(form, text='邮箱地址', font=('Microsoft YaHei', 10),
                 fg='#5f5e5a', bg=bg).pack(anchor='w', pady=(14, 4))
        self.email_var = tk.StringVar()
        email_entry = tk.Entry(form, textvariable=self.email_var,
                               font=('Microsoft YaHei', 11),
                               relief='flat', bd=0,
                               highlightthickness=1,
                               highlightbackground='#d3d1c7',
                               highlightcolor='#2c2c2a')
        email_entry.pack(fill=tk.X, ipady=7)

        # 授权码
        tk.Label(form, text='授权码（非登录密码）',
                 font=('Microsoft YaHei', 10),
                 fg='#5f5e5a', bg=bg).pack(anchor='w', pady=(14, 4))
        self.pwd_var = tk.StringVar()
        self.pwd_entry = tk.Entry(form, textvariable=self.pwd_var,
                                  show='●', font=('Microsoft YaHei', 11),
                                  relief='flat', bd=0,
                                  highlightthickness=1,
                                  highlightbackground='#d3d1c7',
                                  highlightcolor='#2c2c2a')
        self.pwd_entry.pack(fill=tk.X, ipady=7)

        # 显示/隐藏密码
        self.show_pwd = False
        tk.Checkbutton(form, text='显示授权码',
                       font=('Microsoft YaHei', 9),
                       fg='#888780', bg=bg, activebackground=bg,
                       command=self._toggle_pwd).pack(anchor='w', pady=(4, 0))

        # 记住账号
        self.remember_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form, text='记住账号',
                       variable=self.remember_var,
                       font=('Microsoft YaHei', 9),
                       fg='#888780', bg=bg, activebackground=bg).pack(
                           anchor='w')

        # 登录按钮
        self.login_btn = tk.Button(
            form, text='登  录',
            font=('Microsoft YaHei', 12, 'bold'),
            bg='#2c2c2a', fg='white',
            activebackground='#444441', activeforeground='white',
            relief='flat', cursor='hand2',
            command=self._on_login
        )
        self.login_btn.pack(fill=tk.X, ipady=10, pady=(20, 0))

        # 状态提示
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            form, textvariable=self.status_var,
            font=('Microsoft YaHei', 9),
            fg='#E24B4A', bg=bg
        )
        self.status_label.pack(pady=(8, 0))

        # 底部提示
        tk.Label(self.root,
                 text='授权码获取：邮箱设置 → 账户 → 开启POP3/SMTP → 生成授权码',
                 font=('Microsoft YaHei', 8),
                 fg='#b4b2a9', bg=bg).pack(pady=(0, 10))

    # ------------------------------------------------------------------ #
    #  事件处理
    # ------------------------------------------------------------------ #

    def _on_server_change(self, event=None):
        """切换邮箱类型时，自动更新服务器配置"""
        pass  # 服务器地址在登录时从 presets 读取，此处无需额外操作

    def _toggle_pwd(self):
        self.show_pwd = not self.show_pwd
        self.pwd_entry.config(show='' if self.show_pwd else '●')

    def _on_login(self):
        email = self.email_var.get().strip()
        pwd   = self.pwd_var.get().strip()

        if not email:
            self.status_var.set('请输入邮箱地址')
            return
        if not pwd:
            self.status_var.set('请输入授权码')
            return

        # 保存配置
        if self.remember_var.get():
            self._save_config(email, pwd)

        # 禁用按钮，显示等待
        self.login_btn.config(text='连接中...', state=tk.DISABLED)
        self.status_var.set('')

        # 后台线程验证登录，避免界面卡死
        threading.Thread(target=self._do_login,
                         args=(email, pwd), daemon=True).start()

    def _do_login(self, email, pwd):
        """在后台线程中验证账号（尝试 POP3 连接）"""
        try:
            from core.pop3_client import POP3Client
            preset = SERVER_PRESETS.get(self.server_var.get(),
                                        SERVER_PRESETS['QQ邮箱'])
            client = POP3Client(host=preset['pop3_host'],
                                port=preset['pop3_port'])
            client.connect()
            client.login(email, pwd)
            client.quit()

            # 登录成功，切回主线程打开主窗口
            self.root.after(0, self._login_success, email, pwd)

        except Exception as e:
            self.root.after(0, self._login_failed, str(e))

    def _login_success(self, email, pwd):
        from gui.main_window import MainWindow
        preset = SERVER_PRESETS.get(self.server_var.get(),
                                    SERVER_PRESETS['QQ邮箱'])
        account = {
            'email':     email,
            'password':  pwd,
            'smtp_host': preset['smtp_host'],
            'smtp_port': preset['smtp_port'],
            'pop3_host': preset['pop3_host'],
            'pop3_port': preset['pop3_port'],
        }
        # 隐藏登录窗口，打开主窗口
        self.root.withdraw()
        main_win = tk.Toplevel(self.root)
        MainWindow(main_win, account)
        main_win.protocol('WM_DELETE_WINDOW', lambda: self.root.destroy())

    def _login_failed(self, err_msg):
        self.login_btn.config(text='登  录', state=tk.NORMAL)
        self.status_var.set(f'登录失败：{err_msg[:40]}')

    # ------------------------------------------------------------------ #
    #  配置读写（记住账号）
    # ------------------------------------------------------------------ #

    def _save_config(self, email, pwd):
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH, encoding='utf-8')
        if 'account' not in cfg:
            cfg['account'] = {}
        cfg['account']['email']    = email
        cfg['account']['password'] = pwd
        cfg['account']['server']   = self.server_var.get()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            cfg.write(f)

    def _load_config(self):
        """启动时自动填充上次记住的账号"""
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH, encoding='utf-8')
        if 'account' in cfg:
            self.email_var.set(cfg['account'].get('email', ''))
            self.pwd_var.set(cfg['account'].get('password', ''))
            server = cfg['account'].get('server', 'QQ邮箱')
            if server in SERVER_PRESETS:
                self.server_var.set(server)