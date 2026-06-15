# gui/login_window.py
# 成员C负责实现 — 登录窗口
# tkinter 实现，支持 QQ / 163 邮箱快速填充

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import configparser
import os

from utils.theme import (
    BG, CARD, HEADER, TEXT, TEXT_SEC, TEXT_MUTED, TEXT_HINT,
    ACCENT, ACCENT_HOVER, ERROR, HOVER, HEADER_HOVER, DIVIDER,
    BODY, SMALL, TINY, FAMILY,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    make_button,
)

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
        self.root.geometry('440x560')
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 440) // 2
        y = (self.root.winfo_screenheight() - 560) // 2
        self.root.geometry(f'440x560+{x}+{y}')

        self._build_ui()
        self._load_config()

    # ------------------------------------------------------------------ #
    #  界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── 顶部深色区域（带装饰） ──
        header = tk.Frame(self.root, bg=HEADER, height=140)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # 大图标
        tk.Label(header, text='✉️',
                 font=(FAMILY, 36),
                 fg='white', bg=HEADER).pack(pady=(PAD_LG, PAD_XS))
        # 标题
        tk.Label(header, text='Mail Client',
                 font=(FAMILY, 20, 'bold'),
                 fg='white', bg=HEADER).pack()
        # 副标题
        tk.Label(header, text='基于 SMTP / POP3 协议的桌面邮件客户端',
                 font=TINY,
                 fg=TEXT_HINT, bg=HEADER).pack(pady=(PAD_XS, 0))

        # ── 中间白色卡片区域 ──
        card_outer = tk.Frame(self.root, bg=BG)
        card_outer.pack(fill=tk.BOTH, expand=True, padx=PAD_XL, pady=PAD_LG)

        # 卡片容器（白色背景模拟卡片效果）
        card = tk.Frame(card_outer, bg=CARD, padx=PAD_XL, pady=PAD_LG)
        card.pack(fill=tk.BOTH, expand=True)

        # 邮箱类型
        tk.Label(card, text='邮箱类型', font=TINY,
                 fg=TEXT_MUTED, bg=CARD).pack(anchor='w', pady=(0, PAD_XS))
        self.server_var = tk.StringVar(value='QQ邮箱')
        server_cb = ttk.Combobox(card, textvariable=self.server_var,
                                 values=list(SERVER_PRESETS.keys()),
                                 state='readonly', font=BODY,
                                 style='Mail.TCombobox')
        server_cb.pack(fill=tk.X, ipady=PAD_SM, pady=(0, PAD_MD))
        server_cb.bind('<<ComboboxSelected>>', self._on_server_change)

        # 邮箱地址
        tk.Label(card, text='邮箱地址', font=TINY,
                 fg=TEXT_MUTED, bg=CARD).pack(anchor='w', pady=(0, PAD_XS))
        self.email_var = tk.StringVar()
        email_entry = tk.Entry(card, textvariable=self.email_var,
                               font=BODY,
                               relief='flat', bd=0,
                               highlightthickness=1,
                               highlightbackground=DIVIDER,
                               highlightcolor=ACCENT)
        email_entry.pack(fill=tk.X, ipady=8, pady=(0, PAD_MD))

        # 授权码
        tk.Label(card, text='授权码（非登录密码）', font=TINY,
                 fg=TEXT_MUTED, bg=CARD).pack(anchor='w', pady=(0, PAD_XS))
        self.pwd_var = tk.StringVar()
        self.pwd_entry = tk.Entry(card, textvariable=self.pwd_var,
                                  show='●', font=BODY,
                                  relief='flat', bd=0,
                                  highlightthickness=1,
                                  highlightbackground=DIVIDER,
                                  highlightcolor=ACCENT)
        self.pwd_entry.pack(fill=tk.X, ipady=8, pady=(0, PAD_SM))

        # 选项行（显示密码 + 记住账号）
        opts_frame = tk.Frame(card, bg=CARD)
        opts_frame.pack(fill=tk.X, pady=(0, PAD_LG))
        self.show_pwd = False
        tk.Checkbutton(opts_frame, text='显示授权码',
                       font=TINY,
                       fg=TEXT_MUTED, bg=CARD, activebackground=CARD,
                       command=self._toggle_pwd).pack(side=tk.LEFT)
        self.remember_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts_frame, text='记住账号',
                       variable=self.remember_var,
                       font=TINY,
                       fg=TEXT_MUTED, bg=CARD, activebackground=CARD).pack(
                           side=tk.RIGHT)

        # 登录按钮
        self.login_btn = make_button(
            card, text='登  录', command=self._on_login,
            bg=ACCENT, fg='white', hover_bg=ACCENT_HOVER,
            font=(FAMILY, 12, 'bold'), label_padx=PAD_XL, label_pady=PAD_MD,
            fill=tk.X,
        )

        # 状态提示
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            card, textvariable=self.status_var,
            font=TINY, fg=ERROR, bg=CARD,
        )
        self.status_label.pack(pady=(PAD_SM, 0))

        # ── 底部提示 ──
        tk.Label(self.root,
                 text='💡 授权码获取：邮箱设置 → 账户 → 开启POP3/SMTP → 生成授权码',
                 font=TINY, fg=TEXT_HINT, bg=BG).pack(pady=(0, PAD_MD))

    # ------------------------------------------------------------------ #
    #  事件处理
    # ------------------------------------------------------------------ #

    def _on_server_change(self, event=None):
        """切换邮箱类型时，自动更新服务器配置"""
        pass  # 服务器地址在登录时从 presets 读取，此处无需额外操作

    def _toggle_pwd(self):
        self.show_pwd = not self.show_pwd
        self.pwd_entry.config(show='' if self.show_pwd else '●')

    @staticmethod
    def _bind_hover(btn, normal_bg, hover_bg):
        """为按钮绑定 hover 变色效果"""
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
        btn.bind('<Leave>', lambda e: btn.config(bg=normal_bg))

    def _on_login(self):
        if getattr(self, '_logging_in', False):
            return
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
        self._logging_in = True
        self.login_btn.config(text='连接中...', fg=TEXT_MUTED)
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

        def on_main_close():
            """主窗口关闭时（退出登录或点X），回到登录窗口或退出程序"""
            main_win.destroy()
            self.root.deiconify()
            self._logging_in = False
            self.login_btn.config(text='登  录', fg='white')

        main_win._on_logout = on_main_close
        main_win.protocol('WM_DELETE_WINDOW', on_main_close)

    def _login_failed(self, err_msg):
        self._logging_in = False
        self.login_btn.config(text='登  录', fg='white')
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