# gui/compose_window.py
import tkinter as tk

class ComposeWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title('写信')
        self.win.geometry('600x450')
        self._build_ui()

    def _build_ui(self):
        for label in ['收件人：', '主  题：']:
            tk.Label(self.win, text=label).pack(anchor='w', padx=10)
            tk.Entry(self.win, width=60).pack(padx=10, pady=2)

        tk.Label(self.win, text='正  文：').pack(anchor='w', padx=10)
        self.body = tk.Text(self.win, height=15)
        self.body.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        tk.Button(self.win, text='发  送', width=12,
                  command=self.on_send).pack(pady=10)

    def on_send(self):
        pass  # TODO: 成员C完善，调用成员A的SMTPClient