import os
import re
import tempfile
import tkinter as tk
from tkinter import ttk

from tkinterweb import HtmlFrame


class MailPreview:
    def __init__(self, parent):
        self.parent = parent
        self.current_mode = 'text'
        self.cache_root = os.path.join(tempfile.gettempdir(), 'email_client_mail_cache')
        os.makedirs(self.cache_root, exist_ok=True)

        self.container = tk.Frame(parent, bg='white')
        self.container.pack(fill=tk.BOTH, expand=True)

        self.html_frame = HtmlFrame(
            self.container,
            messages_enabled=False,
            horizontal_scrollbar=True,
            vertical_scrollbar=True,
            textwrap=False,
        )
        self.text_frame = tk.Frame(self.container, bg='white')
        self.text_widget = tk.Text(
            self.text_frame,
            font=('Microsoft YaHei', 11),
            fg='#2c2c2a',
            bg='white',
            relief='flat',
            padx=20,
            pady=16,
            wrap=tk.WORD,
            state=tk.DISABLED,
            cursor='arrow',
        )
        self.text_scroll = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=self.text_scroll.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.show_text('（请选择邮件）')

    def clear(self):
        self.show_text('（请选择邮件）')

    def show_text(self, text: str):
        self.current_mode = 'text'
        self.html_frame.pack_forget()
        self.text_frame.pack(fill=tk.BOTH, expand=True)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.insert(tk.END, text if text else '（正文为空）')
        self.text_widget.config(state=tk.DISABLED)

    def show_html(self, html: str, mail_id: int, parts: list):
        if not html:
            self.show_text('（正文为空）')
            return

        self.current_mode = 'html'
        self.text_frame.pack_forget()
        self.html_frame.pack(fill=tk.BOTH, expand=True)

        mail_cache_dir = os.path.join(self.cache_root, str(mail_id or 'preview'))
        os.makedirs(mail_cache_dir, exist_ok=True)
        prepared_html = self._prepare_html(html, mail_cache_dir, parts)
        try:
            self.html_frame.load_html(prepared_html, base_url=f'file:///{mail_cache_dir.replace(os.sep, "/")}/')
        except Exception:
            self.show_text(self._html_to_text(html))

    def _prepare_html(self, html: str, cache_dir: str, parts: list) -> str:
        cid_map = {}
        attachments = []

        for index, part in enumerate(parts, 1):
            filename = part.get('filename') or f'part_{index}.bin'
            filename = self._safe_filename(filename)
            save_path = os.path.join(cache_dir, filename)
            data = part.get('data') or b''
            if data and not os.path.exists(save_path):
                with open(save_path, 'wb') as f:
                    f.write(data)
            file_url = f'file:///{save_path.replace(os.sep, "/")}'
            content_id = (part.get('content_id') or '').strip().strip('<>').strip()
            if content_id:
                cid_map[content_id.lower()] = file_url
            attachments.append((part, file_url))

        def replace_cid(match):
            cid = match.group(1).strip().strip('<>').strip().lower()
            fallback = match.group(0)
            if cid not in cid_map:
                return fallback
            quote = '"' if '"' in fallback else "'"
            return f'src={quote}{cid_map[cid]}{quote}'

        prepared = re.sub(r'src=["\']cid:([^"\']+)["\']', replace_cid, html, flags=re.IGNORECASE)

        attachment_links = []
        for part, file_url in attachments:
            content_type = (part.get('content_type') or '').lower()
            if part.get('is_inline'):
                continue
            if not content_type.startswith('image/'):
                continue
            name = part.get('filename', '图片附件')
            attachment_links.append(
                f'<div style="margin: 12px 0;"><div>{name}</div><img src="{file_url}" style="max-width: 100%; height: auto;" /></div>'
            )

        wrapped = self._wrap_document(prepared)
        if attachment_links:
            wrapped = wrapped.replace(
                '</body>',
                '<hr><div><strong>图片附件预览</strong></div>' + ''.join(attachment_links) + '</body>',
            )

        return wrapped

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]+', '_', name)

    @staticmethod
    def _wrap_document(html: str) -> str:
        base_style = '''
        <style>
            html {
                tkinterweb-overflow-x: auto;
                overflow-y: auto;
                background: #f3f4f6;
            }
            body {
                margin: 0;
                padding: 20px 24px;
                background: #f3f4f6;
                color: #1f2937;
                font-family: "Microsoft YaHei", Arial, sans-serif;
                line-height: 1.6;
                min-width: 760px;
                box-sizing: border-box;
            }
            .mail-shell {
                width: max-content;
                min-width: 720px;
                max-width: 960px;
                margin: 0 auto;
                background: #ffffff;
                padding: 24px 28px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
                box-sizing: border-box;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            table {
                border-collapse: collapse;
            }
            pre {
                white-space: pre-wrap;
                word-break: break-word;
            }
        </style>
        '''
        lower_html = html.lower()
        if '<html' in lower_html:
            wrapped = re.sub(r'<html([^>]*)>', r'<html\1 tkinterweb-overflow-x="auto">', html, count=1, flags=re.IGNORECASE)
            if '<body' in wrapped.lower():
                wrapped = re.sub(r'<body([^>]*)>', r'<body\1>' + base_style + '<div class="mail-shell">', wrapped, count=1, flags=re.IGNORECASE)
                wrapped = re.sub(r'</body>', '</div></body>', wrapped, count=1, flags=re.IGNORECASE)
                return wrapped
            return wrapped.replace('</html>', f'<body>{base_style}<div class="mail-shell"></div></body></html>')
        return f'<html tkinterweb-overflow-x="auto"><body>{base_style}<div class="mail-shell">{html}</div></body></html>'

    @staticmethod
    def _html_to_text(html: str) -> str:
        text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        text = re.sub(r'</?(p|div|li|tr|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip() or '（正文为空）'
