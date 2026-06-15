# gui/compose_window.py
# 成员C负责实现 — 写信窗口

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os

from utils.theme import (
    BG, HEADER, CARD, DIVIDER, TEXT, TEXT_SEC, TEXT_MUTED,
    ACCENT, ACCENT_HOVER, ERROR, HOVER, HEADER_HOVER,
    BODY, SMALL, TINY, FAMILY,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    make_button,
)


class ComposeWindow:
    def __init__(self, parent, account: dict):
        self.account     = account
        self.attachments = []   # 附件路径列表
        self._sending    = False

        self.win = tk.Toplevel(parent)
        self.win.title('写信')
        self.win.geometry('660x540')
        self.win.minsize(520, 420)
        self.win.configure(bg=BG)
        self.win.grab_set()   # 模态窗口

        # 居中
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth()  - 660) // 2
        y = (self.win.winfo_screenheight() - 540) // 2
        self.win.geometry(f'660x540+{x}+{y}')

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self.win, bg=HEADER, height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='✏  写信',
                 font=(FAMILY, 12, 'bold'),
                 fg='white', bg=HEADER).pack(side=tk.LEFT, padx=PAD_LG,
                                             pady=PAD_MD)

        # 发送按钮
        self.send_btn = make_button(
            header, '发  送 ▶', self._on_send,
            bg=ACCENT, fg='white', hover_bg=ACCENT_HOVER,
            font=(FAMILY, 10, 'bold'), label_padx=PAD_LG,
            side=tk.RIGHT, padx=PAD_MD, pady=PAD_SM,
        )

        # 表单区域（用 grid 实现自适应）
        form = tk.Frame(self.win, bg=BG, padx=PAD_XL)
        form.pack(fill=tk.BOTH, expand=True, pady=PAD_MD)

        form.columnconfigure(1, weight=1)

        entry_opts = dict(
            font=BODY,
            relief='flat', bd=0,
            highlightthickness=1,
            highlightbackground=DIVIDER,
            highlightcolor=TEXT,
            bg='white',
        )

        # 发件人（只读显示）
        tk.Label(form, text='发件人：', width=8, anchor='e',
                 font=SMALL,
                 fg=TEXT_MUTED, bg=BG).grid(row=0, column=0, sticky='e',
                                             pady=(0, PAD_SM))
        tk.Label(form, text=self.account['email'],
                 font=SMALL,
                 fg=TEXT_SEC, bg=BG, anchor='w').grid(row=0, column=1,
                                                       sticky='w',
                                                       pady=(0, PAD_SM))

        # 收件人
        tk.Label(form, text='收件人：', width=8, anchor='e',
                 font=SMALL,
                 fg=TEXT_MUTED, bg=BG).grid(row=1, column=0, sticky='e',
                                             pady=(0, PAD_SM))
        self.to_var = tk.StringVar()
        tk.Entry(form, textvariable=self.to_var,
                 **entry_opts).grid(row=1, column=1, sticky='ew',
                                    ipady=PAD_SM, pady=(0, PAD_SM))

        # 主题
        tk.Label(form, text='主  题：', width=8, anchor='e',
                 font=SMALL,
                 fg=TEXT_MUTED, bg=BG).grid(row=2, column=0, sticky='e',
                                             pady=(0, PAD_SM))
        self.subject_var = tk.StringVar()
        tk.Entry(form, textvariable=self.subject_var,
                 **entry_opts).grid(row=2, column=1, sticky='ew',
                                    ipady=PAD_SM, pady=(0, PAD_SM))

        # 正文（grid 布局，rowconfigure 让它拉伸）
        form.rowconfigure(3, weight=1)
        body_frame = tk.Frame(form, bg=BG)
        body_frame.grid(row=3, column=0, columnspan=2, sticky='nsew',
                        pady=(PAD_SM, 0))
        body_frame.rowconfigure(0, weight=1)
        body_frame.columnconfigure(0, weight=1)

        self.body_text = tk.Text(
            body_frame,
            font=BODY,
            fg=TEXT, bg='white',
            relief='flat',
            highlightthickness=1,
            highlightbackground=DIVIDER,
            highlightcolor=TEXT,
            wrap=tk.WORD, padx=PAD_MD, pady=PAD_MD
        )
        body_scroll = ttk.Scrollbar(body_frame, orient=tk.VERTICAL,
                                    command=self.body_text.yview,
                                    style='Mail.Vertical.TScrollbar')
        self.body_text.configure(yscrollcommand=body_scroll.set)
        self.body_text.grid(row=0, column=0, sticky='nsew')
        body_scroll.grid(row=0, column=1, sticky='ns')

        # 底部工具栏
        bottom = tk.Frame(self.win, bg='#ebebeb', height=38)
        bottom.pack(fill=tk.X)
        bottom.pack_propagate(False)

        make_button(
            bottom, '📎 添加附件', self._add_attachment,
            bg=DIVIDER, fg=TEXT_SEC, hover_bg='#c3c1b7',
            font=TINY, label_padx=PAD_MD,
            side=tk.LEFT, pady=PAD_SM,
        )

        self.attach_label = tk.Label(
            bottom, text='',
            font=TINY,
            fg=TEXT_MUTED, bg='#ebebeb', anchor='w'
        )
        self.attach_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar()
        tk.Label(bottom, textvariable=self.status_var,
                 font=TINY,
                 fg=ACCENT, bg='#ebebeb').pack(side=tk.RIGHT, padx=PAD_MD)

    # ------------------------------------------------------------------ #
    #  事件处理
    # ------------------------------------------------------------------ #

    def _add_attachment(self):
        """打开文件选择对话框，添加附件"""
        files = filedialog.askopenfilenames(
            title='选择附件',
            filetypes=[('所有文件', '*.*'),
                       ('PDF文件', '*.pdf'),
                       ('图片', '*.jpg *.jpeg *.png *.gif'),
                       ('文档', '*.docx *.doc *.txt')]
        )
        for f in files:
            if f not in self.attachments:
                self.attachments.append(f)

        if self.attachments:
            names = ', '.join(os.path.basename(f) for f in self.attachments)
            self.attach_label.config(
                text=f'📎 {len(self.attachments)} 个附件：{names[:60]}')

    def _on_send(self):
        if self._sending:
            return
        to_addr = self.to_var.get().strip()
        subject = self.subject_var.get().strip()
        body    = self.body_text.get('1.0', tk.END).strip()

        # 基本验证
        if not to_addr:
            messagebox.showwarning('提示', '请填写收件人地址', parent=self.win)
            return
        if '@' not in to_addr:
            messagebox.showwarning('提示', '收件人地址格式不正确', parent=self.win)
            return
        if not subject:
            if not messagebox.askyesno('提示', '主题为空，确定发送吗？',
                                       parent=self.win):
                return

        # 禁用发送按钮，后台发送
        self._sending = True
        self.send_btn.config(text='发送中...', fg=TEXT_MUTED)
        self.status_var.set('')

        threading.Thread(
            target=self._do_send,
            args=(to_addr, subject, body),
            daemon=True
        ).start()

    def _do_send(self, to_addr, subject, body):
        try:
            from core.smtp_client import SMTPClient
            from db.database import insert_sent

            client = SMTPClient(host=self.account['smtp_host'],
                                port=self.account['smtp_port'])
            client.send(
                username=self.account['email'],
                password=self.account['password'],
                to_addr=to_addr,
                subject=subject,
                body=body,
                attachments=self.attachments if self.attachments else None
            )

            # 存入已发送数据库
            try:
                insert_sent({
                    'to_addr': to_addr,
                    'subject': subject,
                    'body':    body,
                    'status':  'success'
                })
            except Exception:
                pass

            self.win.after(0, self._send_success)

        except Exception as e:
            self.win.after(0, self._send_failed, str(e))

    def _send_success(self):
        self._sending = False
        self.status_var.set('✓ 发送成功')
        self.send_btn.config(text='发  送 ▶', fg='white')
        messagebox.showinfo('发送成功', '邮件已成功发送！', parent=self.win)
        self.win.destroy()

    def _send_failed(self, err_msg):
        self._sending = False
        self.send_btn.config(text='发  送 ▶', fg='white')
        self.status_var.set(f'发送失败')
        messagebox.showerror('发送失败',
                             f'邮件发送失败，请检查网络和授权码。\n\n错误信息：{err_msg}',
                             parent=self.win)

    @staticmethod
    def _bind_hover(btn, normal_bg, hover_bg):
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
        btn.bind('<Leave>', lambda e: btn.config(bg=normal_bg))