# gui/main_window.py
# 成员C负责实现 — 主窗口（三栏布局）

import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from gui.mail_preview import MailPreview
from utils.theme import (
    BG, CARD, HEADER, DIVIDER, DIVIDER_DK,
    TEXT, TEXT_SEC, TEXT_MUTED, TEXT_HINT,
    ACCENT, ERROR, HOVER, HEADER_HOVER,
    SELECT_BG, SELECT_FG, UNREAD_DOT,
    BODY, HEADING, SMALL, TINY, FAMILY,
    PAD_XS, PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    make_button,
)


class MainWindow:
    def __init__(self, root, account: dict):
        """
        account 字典包含:
            email, password, smtp_host, smtp_port, pop3_host, pop3_port
        """
        self.root = root
        self.account = account
        self.mails = []
        self.current_folder = 'inbox'
        self._anim_id = None
        self._fetching = False

        self.root.title(f'邮件客户端 — {account["email"]}')
        self.root.geometry('960x640')
        self.root.minsize(800, 500)
        self.root.configure(bg=BG)

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 960) // 2
        y = (self.root.winfo_screenheight() - 640) // 2
        self.root.geometry(f'960x640+{x}+{y}')

        self._build_ui()
        self.root.after(500, self._fetch_mails)

    # ------------------------------------------------------------------ #
    #  界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # --- 工具栏（保持 pack） ---
        toolbar = tk.Frame(self.root, bg=HEADER, height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        self.btn_compose = make_button(
            toolbar, '✏ 写信', self._open_compose,
            bg='#505050', hover_bg='#666666',
            side=tk.LEFT, pady=PAD_SM, padx=(PAD_MD, PAD_SM),
        )
        self.btn_fetch = make_button(
            toolbar, '⟳ 收信', self._fetch_mails,
            bg='#505050', hover_bg='#666666',
            side=tk.LEFT, pady=PAD_SM, padx=PAD_SM,
        )
        self.btn_delete = make_button(
            toolbar, '🗑 删除', self._delete_selected,
            bg='#505050', hover_bg='#666666',
            side=tk.LEFT, pady=PAD_SM, padx=PAD_SM,
        )

        tk.Label(
            toolbar,
            text=self.account['email'],
            font=TINY,
            fg=TEXT_HINT,
            bg=HEADER,
        ).pack(side=tk.RIGHT, padx=(0, PAD_SM))

        make_button(
            toolbar, '退出', self._logout,
            bg='#505050', hover_bg='#666666', font=TINY,
            label_padx=PAD_SM, label_pady=PAD_XS,
            side=tk.RIGHT, padx=(0, PAD_SM),
        )

        # --- body 区域改用 grid ---
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        body.columnconfigure(0, weight=0)  # 左栏固定
        body.columnconfigure(1, weight=0)  # 分割线
        body.columnconfigure(2, weight=0)  # 中栏固定
        body.columnconfigure(3, weight=0)  # 分割线
        body.columnconfigure(4, weight=1)  # 右栏拉伸
        body.rowconfigure(0, weight=1)

        # 左栏
        left = tk.Frame(body, bg=BG, width=160)
        left.grid(row=0, column=0, sticky='ns')
        left.grid_propagate(False)
        self._build_left(left)

        # 分割线 1
        tk.Frame(body, bg=DIVIDER_DK, width=1).grid(row=0, column=1, sticky='ns')

        # 中栏
        mid = tk.Frame(body, bg=CARD, width=320)
        mid.grid(row=0, column=2, sticky='ns')
        mid.grid_propagate(False)
        self._build_middle(mid)

        # 分割线 2
        tk.Frame(body, bg=DIVIDER_DK, width=1).grid(row=0, column=3, sticky='ns')

        # 右栏
        right = tk.Frame(body, bg=CARD)
        right.grid(row=0, column=4, sticky='nsew')
        self._build_right(right)

        # --- 状态栏（保持 pack） ---
        statusbar = tk.Frame(self.root, bg=DIVIDER, height=1)
        statusbar.pack(fill=tk.X)
        self.status_var = tk.StringVar(value='就绪')
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=TINY,
            fg=TEXT_MUTED,
            bg=BG,
            anchor='w',
        ).pack(fill=tk.X, padx=PAD_MD, pady=PAD_XS)

    def _build_left(self, parent):
        """左栏：文件夹列表"""
        tk.Label(
            parent,
            text='文件夹',
            font=(FAMILY, 10, 'bold'),
            fg=TEXT,
            bg=BG,
        ).pack(anchor='w', padx=PAD_LG, pady=(PAD_LG, PAD_SM))

        # 收件箱（带未读计数）
        inbox_frame = tk.Frame(parent, bg=BG)
        inbox_frame.pack(fill=tk.X, pady=PAD_XS)
        self.folder_btns = {}
        self.folder_btns['inbox'] = make_button(
            inbox_frame, '📥 收件箱', lambda k='inbox': self._switch_folder(k),
            bg=BG, fg=TEXT, hover_bg=HOVER,
            anchor='w', label_padx=PAD_LG, label_pady=PAD_SM,
            fill=tk.X, side=tk.LEFT, expand=True,
        )
        self.unread_label = tk.Label(
            inbox_frame, text='', font=TINY,
            fg=ACCENT, bg=BG, padx=PAD_SM,
        )
        self.unread_label.pack(side=tk.RIGHT, padx=(0, PAD_SM))

        # 已发送
        self.folder_btns['sent'] = make_button(
            parent, '📤 已发送', lambda k='sent': self._switch_folder(k),
            bg=BG, fg=TEXT_SEC, hover_bg=HOVER,
            anchor='w', label_padx=PAD_LG, label_pady=PAD_SM,
            fill=tk.X, pady=PAD_XS,
        )

        # 底部退出区域
        tk.Frame(parent, bg=BG).pack(fill=tk.BOTH, expand=True)

        self._highlight_folder('inbox')

    def _build_middle(self, parent):
        """中栏：邮件列表"""
        self.list_title = tk.Label(
            parent,
            text='收件箱',
            font=(FAMILY, 11, 'bold'),
            fg=TEXT,
            bg=CARD,
            anchor='w',
        )
        self.list_title.pack(fill=tk.X, padx=PAD_LG, pady=(PAD_MD, PAD_SM))

        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X)

        # 搜索框（带 🔍 图标）
        search_frame = tk.Frame(parent, bg=CARD)
        search_frame.pack(fill=tk.X, padx=PAD_MD, pady=PAD_SM)

        tk.Label(search_frame, text='🔍', font=TINY,
                 fg=TEXT_MUTED, bg=CARD).pack(side=tk.LEFT, padx=(0, PAD_XS))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=SMALL,
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=DIVIDER,
            highlightcolor=TEXT,
            fg=TEXT_SEC,
        )
        search_entry.pack(fill=tk.X, ipady=PAD_SM, side=tk.LEFT, expand=True)
        self._add_placeholder(search_entry, '搜索邮件...')

        # Treeview
        cols = ('subject', 'from', 'date')
        self.mail_tree = ttk.Treeview(
            parent, columns=cols, show='headings', selectmode='browse',
            style='Mail.Treeview',
        )
        self.mail_tree.heading('subject', text='主题')
        self.mail_tree.heading('from', text='发件人')
        self.mail_tree.heading('date', text='时间')
        self.mail_tree.column('subject', width=160, stretch=True)
        self.mail_tree.column('from', width=100, stretch=False)
        self.mail_tree.column('date', width=80, stretch=False)

        scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL,
            command=self.mail_tree.yview,
            style='Mail.Vertical.TScrollbar',
        )
        self.mail_tree.configure(yscrollcommand=scrollbar.set)
        self.mail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 未读/已读 tag 样式
        self.mail_tree.tag_configure('unread', font=(FAMILY, 10, 'bold'),
                                     foreground=TEXT)
        self.mail_tree.tag_configure('read', font=SMALL, foreground=TEXT_SEC)

        self.mail_tree.bind('<<TreeviewSelect>>', self._on_mail_select)
        self.search_var.trace('w', self._on_search)

    def _build_right(self, parent):
        """右栏：邮件正文预览"""
        self.header_frame = tk.Frame(parent, bg='#fafaf8', pady=PAD_MD, padx=PAD_LG)
        self.header_frame.pack(fill=tk.X)

        self.lbl_subject = tk.Label(
            self.header_frame,
            text='',
            font=HEADING,
            fg=TEXT,
            bg='#fafaf8',
            anchor='w',
            wraplength=400,
        )
        self.lbl_subject.pack(fill=tk.X)

        # 发件人行（头像 + 邮箱 + 时间）
        from_row = tk.Frame(self.header_frame, bg='#fafaf8')
        from_row.pack(fill=tk.X, pady=(PAD_SM, 0))

        self.avatar_label = tk.Label(
            from_row, text='', font=(FAMILY, 10, 'bold'),
            fg='white', bg=ACCENT, width=2, height=1,
            anchor='center',
        )
        self.avatar_label.pack(side=tk.LEFT, padx=(0, PAD_SM))

        info_frame = tk.Frame(from_row, bg='#fafaf8')
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.lbl_from = tk.Label(
            info_frame, text='', font=SMALL,
            fg=TEXT, bg='#fafaf8', anchor='w',
        )
        self.lbl_from.pack(fill=tk.X)

        self.lbl_date = tk.Label(
            info_frame, text='', font=TINY,
            fg=TEXT_HINT, bg='#fafaf8', anchor='w',
        )
        self.lbl_date.pack(fill=tk.X)

        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X)

        preview_frame = tk.Frame(parent, bg=CARD)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        self.preview = MailPreview(preview_frame)

        self.attach_frame = tk.Frame(parent, bg=BG, pady=PAD_SM, padx=PAD_LG)
        self.attach_label = tk.Label(
            self.attach_frame,
            text='',
            font=TINY,
            fg=TEXT_SEC,
            bg=BG,
            anchor='w',
        )
        self.attach_label.pack(fill=tk.X)

    # ------------------------------------------------------------------ #
    #  辅助方法
    # ------------------------------------------------------------------ #

    def _add_placeholder(self, entry, text):
        """为 Entry 添加占位提示文字"""
        entry.insert(0, text)
        entry.config(fg=TEXT_HINT)

        def on_focus_in(_event):
            if entry.get() == text:
                entry.delete(0, tk.END)
                entry.config(fg=TEXT)

        def on_focus_out(_event):
            if not entry.get():
                entry.insert(0, text)
                entry.config(fg=TEXT_HINT)

        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    def _highlight_folder(self, key):
        for k, btn in self.folder_btns.items():
            if k == key:
                btn.config(bg=HOVER, fg=TEXT)
            else:
                btn.config(bg=BG, fg=TEXT_SEC)

    def _set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    @staticmethod
    def _bind_hover(btn, normal_bg, hover_bg):
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
        btn.bind('<Leave>', lambda e: btn.config(bg=normal_bg))

    def _ensure_mail_content(self, mail: dict):
        """确保邮件拥有 HTML/附件详情，必要时按需重解析"""
        if self.current_folder != 'inbox':
            return mail

        from db.database import get_mail_parts, update_inbox_content

        html_body = mail.get('html_body', '') or ''
        body = mail.get('text_body', '') or mail.get('body', '') or ''
        parts = get_mail_parts(int(mail.get('id', 0))) if mail.get('id') else []

        raw_source = mail.get('raw_eml') or mail.get('raw_data')
        needs_reparse = (
            (not html_body and bool(raw_source))
            or (not body and bool(raw_source))
            or (not parts and bool(raw_source))
        )

        if not needs_reparse:
            mail['parts'] = parts
            mail['text_body'] = body
            return mail

        try:
            from core.mail_parser import parse_mail

            parsed = parse_mail(mail.get('raw_eml') or mail.get('raw_data', ''))
            body = parsed.get('text_body', '') or parsed.get('body', '')
            html_body = parsed.get('html_body', '')
            mail['body'] = body
            mail['text_body'] = body
            mail['html_body'] = html_body
            mail['parts'] = parsed.get('inline_parts', []) + parsed.get('attachments', [])
            if mail.get('id'):
                update_inbox_content(int(mail['id']), parsed)
        except Exception:
            mail['parts'] = parts

        return mail

    def _render_mail_preview(self, mail: dict):
        """根据邮件内容选择 HTML 或纯文本预览"""
        mail = self._ensure_mail_content(mail)
        body = mail.get('text_body', '') or mail.get('body', '') or ''
        html_body = mail.get('html_body', '') or ''
        parts = mail.get('parts', []) or []

        if html_body:
            self.preview.show_html(html_body, int(mail.get('id', 0) or 0), parts)
        else:
            self.preview.show_text(body if body else '（正文为空）')

        attachments = [p for p in parts if not p.get('is_inline')]
        if attachments:
            names = ', '.join(part.get('filename', '附件') for part in attachments)
            self.attach_label.config(text=f'📎 附件：{names}')
            self.attach_frame.pack(fill=tk.X, before=self.header_frame)
        else:
            self.attach_frame.pack_forget()

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
        for item in self.mail_tree.get_children():
            self.mail_tree.delete(item)

        for mail in mails:
            is_unread = not mail.get('is_read')
            tag = 'unread' if is_unread else 'read'
            subject = mail.get('subject', '（无主题）') or '（无主题）'
            if is_unread:
                subject = f'● {subject}'
            sender = mail.get('from_addr', '') or mail.get('to_addr', '')
            date = self._format_date(
                mail.get('receive_time', '') or mail.get('send_time', '')
            )
            self.mail_tree.insert('', tk.END, values=(subject, sender, date),
                                  tags=(tag,), iid=str(mail.get('id', '')))

        self._update_unread_count()
        self._set_status(f'共 {len(mails)} 封邮件')

    @staticmethod
    def _format_date(date_str: str) -> str:
        """格式化日期：今天显示时间，昨天显示'昨天'，更早显示 MM-DD"""
        if not date_str or len(date_str) < 16:
            return date_str
        try:
            dt = datetime.strptime(date_str[:16], '%Y-%m-%d %H:%M')
            now = datetime.now()
            if dt.date() == now.date():
                return dt.strftime('%H:%M')
            elif dt.date() == (now - timedelta(days=1)).date():
                return '昨天'
            else:
                return dt.strftime('%m-%d')
        except Exception:
            return date_str[5:16] if len(date_str) >= 16 else date_str

    def _on_search(self, *_args):
        """搜索过滤邮件列表"""
        keyword = self.search_var.get().strip()
        if not keyword or keyword == '搜索邮件...':
            self._refresh_list(self.mails)
            return
        keyword = keyword.lower()
        filtered = [
            m
            for m in self.mails
            if keyword in (m.get('subject') or '').lower()
            or keyword in (m.get('from_addr') or '').lower()
            or keyword in (m.get('body') or '').lower()
            or keyword in (m.get('text_body') or '').lower()
        ]
        self._refresh_list(filtered)

    def _on_mail_select(self, event=None):
        """点击邮件列表，右栏显示正文"""
        selected = self.mail_tree.selection()
        if not selected:
            return
        mail_id = selected[0]

        mail = next((m for m in self.mails if str(m.get('id', '')) == mail_id), None)
        if not mail:
            return

        if self.current_folder == 'inbox':
            self.mail_tree.item(mail_id, tags=('read',))
            try:
                from db.database import mark_as_read

                mark_as_read(int(mail_id))
                # 更新内存中的状态
                for m in self.mails:
                    if str(m.get('id', '')) == mail_id:
                        m['is_read'] = 1
                        break
            except Exception:
                pass
            self._update_unread_count()

        self.lbl_subject.config(text=mail.get('subject', '（无主题）') or '（无主题）')
        sender = mail.get('from_addr', '') or mail.get('to_addr', '')
        prefix = '收件人：' if self.current_folder == 'sent' else '发件人：'
        self.lbl_from.config(text=f'{prefix}{sender}')
        date = mail.get('receive_time') or mail.get('send_time', '')
        self.lbl_date.config(text=f'时间：{date}')

        # 更新头像
        initial = (sender[0] if sender else '?').upper()
        colors = ['#1D9E75', '#378ADD', '#7F77DD', '#BA7517', '#E24B4A']
        color = colors[hash(sender) % len(colors)]
        self.avatar_label.config(text=initial, bg=color)

        self._render_mail_preview(mail)

    # ------------------------------------------------------------------ #
    #  工具栏操作
    # ------------------------------------------------------------------ #

    def _fetch_mails(self):
        """后台线程收取新邮件"""
        if self._fetching:
            return
        self._fetching = True
        self.btn_fetch.config(fg=TEXT_MUTED)
        self._start_dots_animation(self.btn_fetch, '收信', '⟳ 收信')
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        try:
            from core.pop3_client import POP3Client
            from db.database import insert_inbox

            client = POP3Client(host=self.account['pop3_host'], port=self.account['pop3_port'])
            mails = client.fetch_all(self.account['email'], self.account['password'], max_count=5)
            new_count = 0
            for mail in mails:
                try:
                    insert_inbox(mail)
                    new_count += 1
                except Exception:
                    pass

            self.root.after(0, self._fetch_done, new_count)
        except Exception as e:
            self.root.after(0, self._fetch_failed, str(e))

    def _fetch_done(self, new_count):
        self._stop_dots_animation(self.btn_fetch, '收信')
        self._fetching = False
        self.btn_fetch.config(fg='white')
        self._set_status(f'✓ 收信完成，新邮件 {new_count} 封')
        if self.current_folder == 'inbox':
            self._load_mails_from_db()
        self._update_unread_count()

    def _fetch_failed(self, err_msg):
        self._stop_dots_animation(self.btn_fetch, '收信')
        self._fetching = False
        self.btn_fetch.config(fg='white')
        self._set_status(f'✗ 收信失败: {err_msg}')

    def _start_dots_animation(self, btn, base_text, prefix=''):
        """按钮文字加载动画"""
        self._anim_counter = 0
        self._anim_btn = btn
        self._anim_base = base_text
        dots = ['', '.', '..', '...']
        def tick():
            self._anim_counter = (self._anim_counter + 1) % 4
            btn.config(text=f'{base_text}{dots[self._anim_counter]}')
            self._anim_id = self.root.after(200, tick)
        tick()

    def _stop_dots_animation(self, btn, base_text):
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
            self._anim_id = None
        btn.config(text=base_text)

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

            delete_mail(mail_id, folder=self.current_folder)
            self.mail_tree.delete(selected[0])
            self.mails = [m for m in self.mails if m.get('id') != mail_id]
            self.lbl_subject.config(text='')
            self.lbl_from.config(text='')
            self.lbl_date.config(text='')
            self.preview.clear()
            self.attach_frame.pack_forget()
            self._update_unread_count()
            self._set_status('邮件已删除')
        except Exception as e:
            messagebox.showerror('删除失败', str(e))

    def _open_compose(self):
        from gui.compose_window import ComposeWindow

        ComposeWindow(self.root, self.account)

    def _update_unread_count(self):
        """更新收件箱未读数"""
        if self.current_folder != 'inbox':
            self.unread_label.config(text='')
            return
        count = sum(1 for m in self.mails if not m.get('is_read'))
        if count > 0:
            self.unread_label.config(text=str(count))
        else:
            self.unread_label.config(text='')

    def _logout(self):
        """退出登录，返回登录窗口"""
        if messagebox.askyesno('确认退出', '确定要退出登录吗？'):
            if hasattr(self.root, '_on_logout'):
                self.root._on_logout()
            else:
                self.root.destroy()
