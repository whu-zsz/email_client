# fix_steam.py — 放项目根目录运行：python fix_steam.py
# 专门修复 body 存的是邮件头内容的邮件
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join('data', 'mail.db')

def fix_one(raw_data: str) -> str:
    """
    强健的正文提取：直接找 MIME boundary，
    跳过所有头部处理，直接拿 text/plain 的 payload
    """
    import re, quopri, base64, email
    from email.header import decode_header as _dh

    # 找所有 Content-Type: text/plain 的 part，手动提取
    # 先用标准库尝试
    # 预处理：找第一个 Subject/From/Content-Type 等标准头行，向上回溯找块起始
    _key_re   = re.compile(r'^(From|To|Subject|Content-Type|MIME-Version|Message-ID|Date|Return-Path)\s*:', re.IGNORECASE)
    _hdr_re   = re.compile(r'^[A-Za-z][\w\-]*\s*:\s*\S', re.ASCII)
    _cont_re  = re.compile(r'^\s+\S')
    lines     = raw_data.replace('\r\n', '\n').split('\n')

    # 去重（两段重复内容）
    ct_pos = [i for i, l in enumerate(lines) if re.search(r'Content-Type:.*boundary', l, re.IGNORECASE)]
    if len(ct_pos) >= 2:
        lines = lines[:ct_pos[1]]

    # 找锚点行（From 或 Subject）
    anchor = next((i for i, l in enumerate(lines) if _key_re.match(l)), None)
    if anchor is not None and anchor > 0:
        j = anchor
        while j > 0:
            prev = lines[j-1]
            if _hdr_re.match(prev) or _cont_re.match(prev):
                j -= 1
            else:
                break
        cleaned = '\n'.join(lines[j:])
    else:
        cleaned = '\n'.join(lines)

    msg = email.message_from_string(cleaned)

    # 提取正文
    plain = ''
    html  = ''
    for part in msg.walk():
        ct = part.get_content_type()
        if 'attachment' in str(part.get('Content-Disposition', '')):
            continue
        if ct.startswith('multipart/'):
            continue
        if ct == 'text/plain' and not plain:
            raw_bytes = part.get_payload(decode=True)
            if raw_bytes:
                charset = part.get_content_charset() or 'utf-8'
                for enc in [charset, 'utf-8', 'gbk', 'latin-1']:
                    try:
                        plain = raw_bytes.decode(enc, errors='strict')
                        break
                    except Exception:
                        continue
                if not plain:
                    plain = raw_bytes.decode('utf-8', errors='replace')
        elif ct == 'text/html' and not html:
            raw_bytes = part.get_payload(decode=True)
            if raw_bytes:
                charset = part.get_content_charset() or 'utf-8'
                for enc in [charset, 'utf-8', 'gbk', 'latin-1']:
                    try:
                        html = raw_bytes.decode(enc, errors='strict')
                        break
                    except Exception:
                        continue

    body = plain or html

    # 如果 body 还是空或者看起来像邮件头，说明解析完全失败
    # 最后手段：用正则直接从 raw 里找 QP 或 base64 编码的 text/plain part
    if not body or body.startswith('=?') or 'Content-Type:' in body[:100]:
        # 找 text/plain part 的 payload
        pattern = re.compile(
            r'Content-Type:\s*text/plain[^\n]*\n'
            r'(?:[\w\-]+:[^\n]*\n)*'   # 其他头
            r'(?:Content-Transfer-Encoding:\s*(quoted-printable|base64)[^\n]*\n)?'
            r'\s*\n'                    # 空行
            r'([\s\S]+?)(?=\n--|\Z)',
            re.IGNORECASE
        )
        m = pattern.search(raw_data)
        if m:
            encoding = (m.group(1) or '').lower().strip()
            payload  = m.group(2).strip()
            if encoding == 'quoted-printable':
                try:
                    body = quopri.decodestring(payload.encode()).decode('utf-8', errors='replace')
                except Exception:
                    body = payload
            elif encoding == 'base64':
                try:
                    body = base64.b64decode(payload).decode('utf-8', errors='replace')
                except Exception:
                    body = payload
            else:
                body = payload

    # HTML 去标签 + unicode escape 解码
    if html and not plain:
        import re as _re
        body = _re.sub(r'<br\s*/?>', '\n', body, flags=_re.IGNORECASE)
        body = _re.sub(r'</?(p|div|tr)[^>]*>', '\n', body, flags=_re.IGNORECASE)
        body = _re.sub(r'<[^>]+>', '', body)
        body = _re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), body)
        body = _re.sub(r'\n{3,}', '\n\n', body)

    return body.strip()


# 修复数据库中 body 看起来像邮件头的记录
conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, body, raw_data FROM inbox").fetchall()

fixed = 0
for id_, body, raw_data in rows:
    body = body or ''
    # 判断 body 是否是错误的（包含邮件头特征）
    is_broken = (
        'Content-Type:' in body[:200] or
        body.startswith('=?') or
        body.startswith('Received:') or
        body.startswith('by ') or
        'MIME-Version' in body[:200]
    )
    if not is_broken:
        continue

    print(f"id={id_}: body 异常，重新提取...")
    new_body = fix_one(raw_data or '')
    print(f"  修复结果: {repr(new_body[:60])}")

    conn.execute("UPDATE inbox SET body=? WHERE id=?", (new_body, id_))
    fixed += 1

conn.commit()
conn.close()
print(f"\n完成，共修复 {fixed} 封邮件，重启程序查看效果。")
