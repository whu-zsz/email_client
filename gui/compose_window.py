# gui/compose_window.py
# 成员C负责实现 — 写信窗口

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os


class ComposeWindow:
    def __init__(self, parent, account: dict):
        self.account     = account
        self.attachments = []   # 附件路径列表

        self.win = tk.Toplevel(parent)
        self.win.title('写信')
        self.win.geometry('660x540')
        self.win.minsize(520, 420)
        self.win.configure(bg='#f5f5f0')
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
        bg = '#f5f5f0'

        # 顶部标题栏
        header = tk.Frame(self.win, bg='#2c2c2a', height=46)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text='✏  写信',
                 font=('Microsoft YaHei', 12, 'bold'),
                 fg='white', bg='#2c2c2a').pack(side=tk.LEFT, padx=16,
                                                pady=10)

        # 发送按钮（放在顶部右侧）
        self.send_btn = tk.Button(
            header, text='发  送 ▶',
            font=('Microsoft YaHei', 10, 'bold'),
            bg='#1D9E75', fg='white',
            activebackground='#0F6E56', activeforeground='white',
            relief='flat', cursor='hand2', padx=16,
            command=self._on_send
        )
        self.send_btn.pack(side=tk.RIGHT, padx=12, pady=8)

        # 表单区域
        form = tk.Frame(self.win, bg=bg, padx=20)
        form.pack(fill=tk.BOTH, expand=True, pady=10)

        entry_opts = dict(
            font=('Microsoft YaHei', 11),
            relief='flat', bd=0,
            highlightthickness=1,
            highlightbackground='#d3d1c7',
            highlightcolor='#2c2c2a',
            bg='white'
        )

        # 发件人（只读显示）
        row_from = tk.Frame(form, bg=bg)
        row_from.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_from, text='发件人：', width=8, anchor='e',
                 font=('Microsoft YaHei', 10),
                 fg='#888780', bg=bg).pack(side=tk.LEFT)
        tk.Label(row_from, text=self.account['email'],
                 font=('Microsoft YaHei', 10),
                 fg='#5f5e5a', bg=bg, anchor='w').pack(side=tk.LEFT)

        # 收件人
        row_to = tk.Frame(form, bg=bg)
        row_to.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_to, text='收件人：', width=8, anchor='e',
                 font=('Microsoft YaHei', 10),
                 fg='#888780', bg=bg).pack(side=tk.LEFT)
        self.to_var = tk.StringVar()
        tk.Entry(row_to, textvariable=self.to_var,
                 **entry_opts).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                    ipady=6)

        # 主题
        row_sub = tk.Frame(form, bg=bg)
        row_sub.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_sub, text='主  题：', width=8, anchor='e',
                 font=('Microsoft YaHei', 10),
                 fg='#888780', bg=bg).pack(side=tk.LEFT)
        self.subject_var = tk.StringVar()
        tk.Entry(row_sub, textvariable=self.subject_var,
                 **entry_opts).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                    ipady=6)

        # 分割线
        tk.Frame(form, bg='#d3d1c7', height=1).pack(fill=tk.X, pady=4)

        # 正文
        body_frame = tk.Frame(form, bg=bg)
        body_frame.pack(fill=tk.BOTH, expand=True)
        self.body_text = tk.Text(
            body_frame,
            font=('Microsoft YaHei', 11),
            fg='#2c2c2a', bg='white',
            relief='flat',
            highlightthickness=1,
            highlightbackground='#d3d1c7',
            wrap=tk.WORD, padx=10, pady=10
        )
        body_scroll = ttk.Scrollbar(body_frame, orient=tk.VERTICAL,
                                    command=self.body_text.yview)
        self.body_text.configure(yscrollcommand=body_scroll.set)
        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部工具栏（附件 + 状态）
        bottom = tk.Frame(self.win, bg='#ebebeb', height=38)
        bottom.pack(fill=tk.X)
        bottom.pack_propagate(False)

        tk.Button(
            bottom, text='📎 添加附件',
            font=('Microsoft YaHei', 9),
            bg='#ebebeb', fg='#5f5e5a',
            activebackground='#d3d1c7',
            relief='flat', cursor='hand2', padx=10,
            command=self._add_attachment
        ).pack(side=tk.LEFT, pady=6)

        self.attach_label = tk.Label(
            bottom, text='',
            font=('Microsoft YaHei', 9),
            fg='#888780', bg='#ebebeb', anchor='w'
        )
        self.attach_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar()
        tk.Label(bottom, textvariable=self.status_var,
                 font=('Microsoft YaHei', 9),
                 fg='#1D9E75', bg='#ebebeb').pack(side=tk.RIGHT, padx=12)

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
        self.send_btn.config(text='发送中...', state=tk.DISABLED)
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
        self.status_var.set('✓ 发送成功')
        self.send_btn.config(text='发  送 ▶', state=tk.NORMAL)
        messagebox.showinfo('发送成功', '邮件已成功发送！', parent=self.win)
        self.win.destroy()

    def _send_failed(self, err_msg):
        self.send_btn.config(text='发  送 ▶', state=tk.NORMAL)
        self.status_var.set(f'发送失败')
        messagebox.showerror('发送失败',
                             f'邮件发送失败，请检查网络和授权码。\n\n错误信息：{err_msg}',
                             parent=self.win)