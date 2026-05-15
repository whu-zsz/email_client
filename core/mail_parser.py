# core/mail_parser.py
# 成员B负责实现 — 邮件解析模块
# 解析从 POP3 获取的原始 RFC 2822 格式邮件

import email
import os
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from utils.logger import logger


def _decode_str(encoded: str) -> str:
    """
    解码邮件头字段中的编码字符串
    处理 Base64 编码（=?utf-8?B?...?=）和
    Quoted-Printable 编码（=?utf-8?Q?...?=）的中文
    """
    if not encoded:
        return ''
    parts = decode_header(encoded)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            charset = charset or 'utf-8'
            try:
                result.append(part.decode(charset, errors='replace'))
            except (LookupError, UnicodeDecodeError):
                result.append(part.decode('utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def _decode_part(part) -> str:
    """安全解码一个 MIME part 的 payload，尝试多种编码"""
    raw_bytes = part.get_payload(decode=True)
    if raw_bytes is None:
        return ''
    charset = part.get_content_charset()
    for enc in [charset, 'utf-8', 'gbk', 'gb2312', 'latin-1']:
        if not enc:
            continue
        try:
            return raw_bytes.decode(enc, errors='strict')
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode('utf-8', errors='replace')


def _get_body(msg) -> str:
    """
    从邮件对象中提取纯文本正文
    优先取 text/plain，备用 text/html，再备用任意可读 part
    兼容 QQ 系统通知、嵌套 multipart/alternative 等特殊格式
    """
    plain_body = ''
    html_body  = ''

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get('Content-Disposition', ''))

        if 'attachment' in disposition:
            continue
        if content_type.startswith('multipart/'):
            continue

        if content_type == 'text/plain' and not plain_body:
            plain_body = _decode_part(part)
        elif content_type == 'text/html' and not html_body:
            html_body = _strip_html(_decode_part(part))

    body = plain_body or html_body

    # 最终兜底：非 multipart 且上面都没取到时
    if not body and not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode('utf-8', errors='replace')
        else:
            raw = msg.get_payload()
            if isinstance(raw, str):
                body = raw

    return body.strip()


def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本内容，并处理 JS 风格 \\uXXXX Unicode 转义"""
    import re
    # 把 <br>、<p>、<div>、<tr> 换成换行
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?(p|div|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
    # 去掉其他所有标签
    html = re.sub(r'<[^>]+>', '', html)
    # 解码 JS 风格的 Unicode 转义（如 QQ 退信模板中的 \\u90ae）
    html = re.sub(r'\\u([0-9a-fA-F]{4})',
                  lambda m: chr(int(m.group(1), 16)), html)
    # 合并多余空行
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()



def _get_attachments(msg, save_dir: str = None) -> list:
    """
    提取邮件中的所有附件信息

    参数:
        msg      : email.message 对象
        save_dir : 若指定目录，则自动将附件保存到该目录

    返回:
        list of dict，每个附件包含:
            filename : 文件名
            data     : bytes 原始数据
            saved_path: 保存路径（若 save_dir 不为 None）
    """
    attachments = []

    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        disposition = str(part.get('Content-Disposition', ''))
        if 'attachment' not in disposition:
            continue

        # 解码文件名（可能是中文编码）
        filename = part.get_filename()
        if filename:
            filename = _decode_str(filename)
        else:
            filename = f'attachment_{len(attachments) + 1}'

        data = part.get_payload(decode=True)
        if data is None:
            continue

        entry = {'filename': filename, 'data': data, 'saved_path': None}

        # 可选：保存到本地目录
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            with open(save_path, 'wb') as f:
                f.write(data)
            entry['saved_path'] = save_path
            logger.info(f'[Parser] 附件已保存: {save_path}')

        attachments.append(entry)

    return attachments


def parse_mail(raw_data: str, save_attachments_dir: str = None) -> dict:
    """
    解析原始邮件字符串，返回结构化字典

    参数:
        raw_data             : POP3 RETR 返回的原始邮件字符串
        save_attachments_dir : 若指定，附件自动保存到此目录

    返回字典结构:
        {
            'from'        : '发件人名称 <地址>',
            'from_addr'   : '发件人邮箱地址',
            'to'          : '收件人',
            'subject'     : '主题（已解码中文）',
            'date'        : '日期字符串',
            'body'        : '纯文本正文',
            'attachments' : [ {'filename':..., 'data':..., 'saved_path':...} ],
            'raw'         : '原始字符串（供调试）'
        }
    """
    # ── 预处理：以 "From:" 为锚点，向上回溯找连续头字段块的起始
    # 可靠处理 QQ 邮件开头的多行非标准续行、重复内容等情况
    import re as _re
    _strict_hdr = _re.compile(r'^[A-Za-z][\w\-]*\s*:\s*\S', _re.ASCII)
    _lines      = raw_data.split('\n')
    # 去重：若邮件内容在 raw_data 里出现两次（POP3 bug），只取第一段
    _boundary_re = _re.compile(r'Content-Type:.*boundary', _re.IGNORECASE)
    _ct_positions = [i for i, l in enumerate(_lines) if _boundary_re.search(l)]
    if len(_ct_positions) >= 2:
        _lines = _lines[:_ct_positions[1]]   # 截掉第二段重复内容
    # 找第一个 From: 行作为锚点
    _from_idx = next(
        (i for i, l in enumerate(_lines) if _re.match(r'^From\s*:', l, _re.IGNORECASE)),
        None
    )
    if _from_idx is not None and _from_idx > 0:
        _j = _from_idx
        while _j > 0:
            _prev = _lines[_j - 1]
            if _strict_hdr.match(_prev) or _re.match(r'^\s+\S', _prev):
                _j -= 1
            else:
                break
        cleaned_data = '\n'.join(_lines[_j:])
    else:
        cleaned_data = '\n'.join(_lines)

    try:
        msg = email.message_from_string(cleaned_data)
    except Exception as e:
        logger.error(f'[Parser] 邮件解析失败: {e}')
        return {
            'from': '', 'from_addr': '', 'to': '',
            'subject': '（解析失败）', 'date': '',
            'body': raw_data, 'attachments': [], 'raw': raw_data
        }

    # ---- 解析头部字段 ----
    subject   = _decode_str(msg.get('Subject', ''))
    from_raw  = _decode_str(msg.get('From',    ''))
    to_raw    = _decode_str(msg.get('To',      ''))
    date_raw  = msg.get('Date', '')

    # 提取纯邮箱地址（去掉显示名称）
    _, from_addr = parseaddr(from_raw)

    # 日期格式化
    try:
        date_str = parsedate_to_datetime(date_raw).strftime('%Y-%m-%d %H:%M')
    except Exception:
        date_str = date_raw

    # ---- 解析正文 ----
    body = _get_body(msg)

    # ---- 解析附件 ----
    attachments = _get_attachments(msg, save_dir=save_attachments_dir)

    result = {
        'from'        : from_raw,
        'from_addr'   : from_addr,
        'to'          : to_raw,
        'subject'     : subject,
        'date'        : date_str,
        'body'        : body,
        'attachments' : attachments,
        'raw'         : raw_data
    }

    logger.info(f'[Parser] 解析完成 | 发件人: {from_addr} | 主题: {subject}')
    return result