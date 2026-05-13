# gui/main_window.py
# 成员C负责实现 — 主窗口（三栏布局）

import tkinter as tk
from tkinter import ttk, messagebox
import threading


class MainWindow:
    def __init__(self, root, account: dict):
        """
        account 字典包含:
            email, password, smtp_host, smtp_port, pop3_host, pop3_port
        """
        self.root    = root
        self.account = account
        self.mails   = []        # 当前显示的邮件列表
        self.current_folder = 'inbox'  # 当前文件夹

        self.root.title(f'邮件客户端 — {account["email"]}')
        self.root.geometry('960x640')
        self.root.minsize(800, 500)
        self.root.configure(bg='#f5f5f0')

        # 居中
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 960) // 2
        y = (self.root.winfo_screenheight() - 640) // 2
        self.root.geometry(f'960x640+{x}+{y}')

        self._build_ui()
        # 启动后自动收取一次邮件
        self.root.after(500, self._fetch_mails)

    # ------------------------------------------------------------------ #
    #  界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── 顶部工具栏 ──────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, bg='#2c2c2a', height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        btn_style = dict(font=('Microsoft YaHei', 10),
                         bg='#2c2c2a', fg='white',
                         activebackground='#444441', activeforeground='white',
                         relief='flat', cursor='hand2', padx=14)

        tk.Button(toolbar, text='✏ 写信',
                  command=self._open_compose, **btn_style).pack(
                      side=tk.LEFT, pady=8)
        tk.Button(toolbar, text='⟳ 收信',
                  command=self._fetch_mails, **btn_style).pack(
                      side=tk.LEFT, pady=8)
        tk.Button(toolbar, text='🗑 删除',
                  command=self._delete_selected, **btn_style).pack(
                      side=tk.LEFT, pady=8)

        # 账户信息（右侧）
        tk.Label(toolbar, text=self.account['email'],
                 font=('Microsoft YaHei', 9),
                 fg='#b4b2a9', bg='#2c2c2a').pack(side=tk.RIGHT, padx=16)

        # ── 主体区域（三栏）────────────────────────────────────────────
        body = tk.Frame(self.root, bg='#f5f5f0')
        body.pack(fill=tk.BOTH, expand=True)

        # 左栏：文件夹
        self._build_left(body)

        # 分割线
        tk.Frame(body, bg='#d3d1c7', width=1).pack(side=tk.LEFT, fill=tk.Y)

        # 中栏：邮件列表
        self._build_middle(body)

        # 分割线
        tk.Frame(body, bg='#d3d1c7', width=1).pack(side=tk.LEFT, fill=tk.Y)

        # 右栏：正文预览
        self._build_right(body)

        # ── 状态栏 ──────────────────────────────────────────────────────
        statusbar = tk.Frame(self.root, bg='#d3d1c7', height=1)
        statusbar.pack(fill=tk.X)
        self.status_var = tk.StringVar(value='就绪')
        tk.Label(self.root, textvariable=self.status_var,
                 font=('Microsoft YaHei', 9),
                 fg='#888780', bg='#f5f5f0',
                 anchor='w').pack(fill=tk.X, padx=10, pady=3)

    def _build_left(self, parent):
        """左栏：文件夹列表"""
        left = tk.Frame(parent, bg='#f5f5f0', width=150)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='文件夹',
                 font=('Microsoft YaHei', 10, 'bold'),
                 fg='#2c2c2a', bg='#f5f5f0').pack(anchor='w', padx=16, pady=(16, 8))

        folders = [('inbox', '📥 收件箱'), ('sent', '📤 已发送')]
        self.folder_btns = {}
        for key, label in folders:
            btn = tk.Button(
                left, text=label, anchor='w',
                font=('Microsoft YaHei', 10),
                fg='#2c2c2a', bg='#f5f5f0',
                activebackground='#e8e8e4',
                relief='flat', cursor='hand2', padx=16, pady=6,
                command=lambda k=key: self._switch_folder(k)
            )
            btn.pack(fill=tk.X)
            self.folder_btns[key] = btn

        # 默认高亮收件箱
        self._highlight_folder('inbox')

    def _build_middle(self, parent):
        """中栏：邮件列表"""
        mid = tk.Frame(parent, bg='white', width=320)
        mid.pack(side=tk.LEFT, fill=tk.BOTH)
        mid.pack_propagate(False)

        # 列表标题
        self.list_title = tk.Label(
            mid, text='收件箱',
            font=('Microsoft YaHei', 11, 'bold'),
            fg='#2c2c2a', bg='white', anchor='w'
        )
        self.list_title.pack(fill=tk.X, padx=14, pady=(12, 6))

        tk.Frame(mid, bg='#d3d1c7', height=1).pack(fill=tk.X)

        # 搜索框
        search_frame = tk.Frame(mid, bg='white')
        search_frame.pack(fill=tk.X, padx=10, pady=6)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=('Microsoft YaHei', 10),
            relief='flat', bd=0,
            highlightthickness=1,
            highlightbackground='#d3d1c7',
            highlightcolor='#2c2c2a',
            fg='#5f5e5a'
        )
        search_entry.pack(fill=tk.X, ipady=5, padx=2)
        # 占位提示
        self._add_placeholder(search_entry, '搜索邮件...')

        # 邮件列表（Treeview）
        cols = ('subject', 'from', 'date')
        self.mail_tree = ttk.Treeview(mid, columns=cols,
                                      show='headings', selectmode='browse')
        self.mail_tree.heading('subject', text='主题')
        self.mail_tree.heading('from',    text='发件人')
        self.mail_tree.heading('date',    text='时间')
        self.mail_tree.column('subject', width=160, stretch=True)
        self.mail_tree.column('from',    width=100, stretch=False)
        self.mail_tree.column('date',    width=80,  stretch=False)

        # 滚动条
        scrollbar = ttk.Scrollbar(mid, orient=tk.VERTICAL,
                                  command=self.mail_tree.yview)
        self.mail_tree.configure(yscrollcommand=scrollbar.set)
        self.mail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 已读/未读样式
        self.mail_tree.tag_configure('unread',
                                     font=('Microsoft YaHei', 10, 'bold'))
        self.mail_tree.tag_configure('read',
                                     font=('Microsoft YaHei', 10))

        self.mail_tree.bind('<<TreeviewSelect>>', self._on_mail_select)
        self.mail_tree.bind('<Double-1>', self._on_mail_select)

    def _build_right(self, parent):
        """右栏：邮件正文预览"""
        right = tk.Frame(parent, bg='white')
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 邮件头部信息
        self.header_frame = tk.Frame(right, bg='#fafaf8',
                                     pady=12, padx=16)
        self.header_frame.pack(fill=tk.X)

        self.lbl_subject = tk.Label(
            self.header_frame, text='',
            font=('Microsoft YaHei', 13, 'bold'),
            fg='#2c2c2a', bg='#fafaf8', anchor='w', wraplength=400
        )
        self.lbl_subject.pack(fill=tk.X)

        self.lbl_from = tk.Label(
            self.header_frame, text='',
            font=('Microsoft YaHei', 9),
            fg='#888780', bg='#fafaf8', anchor='w'
        )
        self.lbl_from.pack(fill=tk.X, pady=(4, 0))

        self.lbl_date = tk.Label(
            self.header_frame, text='',
            font=('Microsoft YaHei', 9),
            fg='#b4b2a9', bg='#fafaf8', anchor='w'
        )
        self.lbl_date.pack(fill=tk.X)

        tk.Frame(right, bg='#d3d1c7', height=1).pack(fill=tk.X)

        # 正文文本框
        text_frame = tk.Frame(right, bg='white')
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.body_text = tk.Text(
            text_frame,
            font=('Microsoft YaHei', 11),
            fg='#2c2c2a', bg='white',
            relief='flat', padx=20, pady=16,
            wrap=tk.WORD, state=tk.DISABLED,
            cursor='arrow'
        )
        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                                    command=self.body_text.yview)
        self.body_text.configure(yscrollcommand=text_scroll.set)
        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 附件栏（默认隐藏）
        self.attach_frame = tk.Frame(right, bg='#f5f5f0', pady=8, padx=16)
        self.attach_label = tk.Label(
            self.attach_frame, text='',
            font=('Microsoft YaHei', 9),
            fg='#5f5e5a', bg='#f5f5f0', anchor='w'
        )
        self.attach_label.pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    #  辅助方法
    # ------------------------------------------------------------------ #

    def _add_placeholder(self, entry, text):
        """为 Entry 添加占位提示文字"""
        entry.insert(0, text)
        entry.config(fg='#b4b2a9')

        def on_focus_in(e):
            if entry.get() == text:
                entry.delete(0, tk.END)
                entry.config(fg='#2c2c2a')

        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, text)
                entry.config(fg='#b4b2a9')

        entry.bind('<FocusIn>',  on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    def _highlight_folder(self, key):
        for k, btn in self.folder_btns.items():
            if k == key:
                btn.config(bg='#e8e8e4', fg='#2c2c2a')
            else:
                btn.config(bg='#f5f5f0', fg='#5f5e5a')

    def _set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    # ------------------------------------------------------------------ #
    #  邮件列表操作
    # ------------------------------------------------------------------ #

    def _switch_folder(self, folder):
        self.current_folder = folder
        self._highlight_folder(folder)
        folder_names = {'inbox': '收件箱', 'sent': '已发送'}
        self.list_title.config(text=folder_names.get(folder, folder))
        self._load_mails_from_db()

    def _load_mails_from_db(self):
        """从数据库加载邮件列表（由同学D实现数据库后对接）"""
        try:
            from db.database import get_inbox, get_sent
            if self.current_folder == 'inbox':
                self.mails = get_inbox()
            else:
                self.mails = get_sent()
            self._refresh_list(self.mails)
        except Exception as e:
            self._set_status(f'加载邮件失败: {e}')

    def _refresh_list(self, mails: list):
        """刷新中栏邮件列表"""
        # 清空列表
        for item in self.mail_tree.get_children():
            self.mail_tree.delete(item)

        for mail in mails:
            tag = 'read' if mail.get('is_read') else 'unread'
            subject = mail.get('subject', '（无主题）') or '（无主题）'
            sender  = mail.get('from_addr', '') or mail.get('to_addr', '')
            date    = mail.get('receive_time', '') or mail.get('send_time', '')
            # 日期只显示月-日 时:分
            if date and len(date) >= 16:
                date = date[5:16]
            self.mail_tree.insert('', tk.END,
                                  values=(subject, sender, date),
                                  tags=(tag,),
                                  iid=str(mail.get('id', '')))

        self._set_status(f'共 {len(mails)} 封邮件')

    def _on_search(self, *args):
        """搜索过滤邮件列表"""
        keyword = self.search_var.get().strip()
        if not keyword or keyword == '搜索邮件...':
            self._refresh_list(self.mails)
            return
        keyword = keyword.lower()
        filtered = [m for m in self.mails
                    if keyword in (m.get('subject') or '').lower()
                    or keyword in (m.get('from_addr') or '').lower()
                    or keyword in (m.get('body') or '').lower()]
        self._refresh_list(filtered)

    def _on_mail_select(self, event=None):
        """点击邮件列表，右栏显示正文"""
        selected = self.mail_tree.selection()
        if not selected:
            return
        mail_id = selected[0]

        # 找到对应邮件
        mail = next((m for m in self.mails
                     if str(m.get('id', '')) == mail_id), None)
        if not mail:
            return

        # 标记已读
        self.mail_tree.item(mail_id, tags=('read',))
        try:
            from db.database import mark_as_read
            mark_as_read(int(mail_id))
        except Exception:
            pass

        # 显示邮件内容
        self.lbl_subject.config(text=mail.get('subject', '（无主题）') or '（无主题）')
        self.lbl_from.config(
            text=f'发件人：{mail.get("from_addr", "") or mail.get("to_addr", "")}')
        date = mail.get('receive_time') or mail.get('send_time', '')
        self.lbl_date.config(text=f'时间：{date}')

        body = mail.get('body', '') or ''
        self.body_text.config(state=tk.NORMAL)
        self.body_text.delete('1.0', tk.END)
        self.body_text.insert(tk.END, body)
        self.body_text.config(state=tk.DISABLED)

        # 附件提示
        attachments = mail.get('attachments', [])
        if attachments:
            names = ', '.join(
                a.get('filename', '附件') for a in attachments)
            self.attach_label.config(text=f'📎 附件：{names}')
            self.attach_frame.pack(fill=tk.X, before=self.header_frame)
        else:
            self.attach_frame.pack_forget()

    # ------------------------------------------------------------------ #
    #  工具栏操作
    # ------------------------------------------------------------------ #

    def _fetch_mails(self):
        """后台线程收取新邮件"""
        self._set_status('正在收取邮件...')
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        try:
            from core.pop3_client import POP3Client
            from db.database import insert_inbox

            client = POP3Client(host=self.account['pop3_host'],
                                port=self.account['pop3_port'])
            mails = client.fetch_all(
                self.account['email'],
                self.account['password'],
                max_count=20
            )
            new_count = 0
            for m in mails:
                try:
                    insert_inbox(m)
                    new_count += 1
                except Exception:
                    pass  # 重复邮件跳过

            self.root.after(0, self._fetch_done, new_count)
        except Exception as e:
            self.root.after(0, self._set_status, f'收信失败: {e}')

    def _fetch_done(self, new_count):
        self._set_status(f'收信完成，新邮件 {new_count} 封')
        if self.current_folder == 'inbox':
            self._load_mails_from_db()

    def _delete_selected(self):
        selected = self.mail_tree.selection()
        if not selected:
            messagebox.showinfo('提示', '请先选择一封邮件')
            return
        if not messagebox.askyesno('确认删除', '确定要删除这封邮件吗？'):
            return
        mail_id = int(selected[0])
        try:
            from db.database import delete_mail
            delete_mail(mail_id)
            self.mail_tree.delete(selected[0])
            self.mails = [m for m in self.mails if m.get('id') != mail_id]
            # 清空右栏
            self.lbl_subject.config(text='')
            self.lbl_from.config(text='')
            self.lbl_date.config(text='')
            self.body_text.config(state=tk.NORMAL)
            self.body_text.delete('1.0', tk.END)
            self.body_text.config(state=tk.DISABLED)
            self._set_status('邮件已删除')
        except Exception as e:
            messagebox.showerror('删除失败', str(e))

    def _open_compose(self):
        from gui.compose_window import ComposeWindow
        ComposeWindow(self.root, self.account)