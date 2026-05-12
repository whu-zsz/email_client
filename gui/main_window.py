# gui/main_window.py
import tkinter as tk
from tkinter import ttk

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title('邮件客户端')
        self.root.geometry('900x600')
        self._build_ui()

    def _build_ui(self):
        # 左侧文件夹栏
        left = tk.Frame(self.root, width=150, bg='#f0f0f0')
        left.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(left, text='收件箱', bg='#f0f0f0').pack(pady=5)
        tk.Label(left, text='已发送', bg='#f0f0f0').pack(pady=5)

        # 中间邮件列表
        mid = tk.Frame(self.root, width=300)
        mid.pack(side=tk.LEFT, fill=tk.BOTH)
        self.mail_list = ttk.Treeview(mid,
            columns=('from', 'subject', 'time'), show='headings')
        self.mail_list.heading('from',    text='发件人')
        self.mail_list.heading('subject', text='主题')
        self.mail_list.heading('time',    text='时间')
        self.mail_list.pack(fill=tk.BOTH, expand=True)

        # 右侧正文预览
        right = tk.Frame(self.root)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.body_text = tk.Text(right, wrap=tk.WORD)
        self.body_text.pack(fill=tk.BOTH, expand=True)