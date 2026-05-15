# core/mail_parser.py
# 成员B负责实现 — 邮件解析模块
# 解析从 POP3 获取的原始 RFC 2822 格式邮件

import email
import mimetypes
import os
import re
from email import policy
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from utils.logger import logger


INLINE_DISPOSITION = 'inline'
ATTACHMENT_DISPOSITION = 'attachment'


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



def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本内容，并处理 JS 风格 \\uXXXX Unicode 转义"""
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?(p|div|tr|li|ul|ol|table|tbody|thead|h[1-6])[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    html = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()



def _normalize_content_id(value: str) -> str:
    """规范化 Content-ID，去掉尖括号和空白"""
    return (value or '').strip().strip('<>').strip()



def _guess_extension(content_type: str) -> str:
    """按 content-type 猜测文件扩展名"""
    ext = mimetypes.guess_extension(content_type or '') or ''
    if ext == '.jpe':
        return '.jpg'
    return ext or '.bin'



def _make_part_filename(part, index: int, prefix: str) -> str:
    """生成附件或内嵌资源文件名"""
    filename = part.get_filename()
    if filename:
        return _decode_str(filename)
    ext = _guess_extension(part.get_content_type())
    return f'{prefix}_{index}{ext}'



def _save_part_data(entry: dict, save_dir: str = None) -> dict:
    """按需把 MIME part 保存到本地目录"""
    entry['saved_path'] = None
    if save_dir and entry.get('data'):
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, entry['filename'])
        with open(save_path, 'wb') as f:
            f.write(entry['data'])
        entry['saved_path'] = save_path
        logger.info(f'[Parser] 资源已保存: {save_path}')
    return entry



def _extract_bodies(msg) -> tuple:
    """提取纯文本与 HTML 正文"""
    plain_body = ''
    html_body = ''

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or '').lower()

        if content_type.startswith('multipart/'):
            continue
        if disposition == ATTACHMENT_DISPOSITION:
            continue

        if content_type == 'text/plain' and not plain_body:
            plain_body = _decode_part(part)
        elif content_type == 'text/html' and not html_body:
            html_body = _decode_part(part)

    if not plain_body and html_body:
        plain_body = _strip_html(html_body)

    if not plain_body and not html_body and not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        decoded = ''
        if payload:
            for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    decoded = payload.decode(enc, errors='strict')
                    break
                except UnicodeDecodeError:
                    continue
            if not decoded:
                decoded = payload.decode('utf-8', errors='replace')
        else:
            raw = msg.get_payload()
            if isinstance(raw, str):
                decoded = raw

        if msg.get_content_type() == 'text/html':
            html_body = decoded
            plain_body = _strip_html(decoded)
        else:
            plain_body = decoded

    return plain_body.strip(), html_body.strip()



def _extract_parts(msg, save_dir: str = None) -> tuple:
    """提取附件与内嵌资源"""
    attachments = []
    inline_parts = []
    attachment_index = 1
    inline_index = 1

    if not msg.is_multipart():
        return attachments, inline_parts

    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type.startswith('multipart/'):
            continue

        data = part.get_payload(decode=True)
        if data is None:
            continue

        disposition = (part.get_content_disposition() or '').lower()
        content_id = _normalize_content_id(part.get('Content-ID', ''))
        maintype = part.get_content_maintype()
        filename = part.get_filename()
        is_inline = disposition == INLINE_DISPOSITION or bool(content_id)

        if maintype == 'text' and not filename and not content_id and disposition != ATTACHMENT_DISPOSITION:
            continue

        if is_inline and maintype != 'text':
            entry = {
                'filename': _make_part_filename(part, inline_index, 'inline'),
                'data': data,
                'content_type': content_type,
                'content_id': content_id,
                'disposition': disposition or INLINE_DISPOSITION,
                'is_inline': True,
                'size': len(data),
            }
            inline_parts.append(_save_part_data(entry, save_dir))
            inline_index += 1
            continue

        if disposition == ATTACHMENT_DISPOSITION or filename or maintype != 'text':
            entry = {
                'filename': _make_part_filename(part, attachment_index, 'attachment'),
                'data': data,
                'content_type': content_type,
                'content_id': content_id,
                'disposition': disposition or ATTACHMENT_DISPOSITION,
                'is_inline': False,
                'size': len(data),
            }
            attachments.append(_save_part_data(entry, save_dir))
            attachment_index += 1

    return attachments, inline_parts



def _preprocess_raw_text(raw_text: str) -> str:
    """清理前导噪声并兼容折叠头字段"""
    strict_hdr = re.compile(r'^[A-Za-z][\w\-]*\s*:.*$', re.ASCII)
    anchor_hdr = re.compile(
        r'^(From|To|Subject|Date|MIME-Version|Content-Type|Content-Transfer-Encoding|Message-ID|Return-Path)\s*:',
        re.IGNORECASE,
    )
    lines = raw_text.replace('\r\n', '\n').split('\n')

    boundary_re = re.compile(r'Content-Type:.*boundary', re.IGNORECASE)
    ct_positions = [i for i, line in enumerate(lines) if boundary_re.search(line)]
    if len(ct_positions) >= 2:
        lines = lines[:ct_positions[1]]

    anchor_idx = next((i for i, line in enumerate(lines) if anchor_hdr.match(line)), None)
    if anchor_idx is None or anchor_idx <= 0:
        return '\n'.join(lines)

    start = anchor_idx
    while start > 0:
        prev = lines[start - 1]
        if strict_hdr.match(prev) or re.match(r'^\s+', prev):
            start -= 1
            continue
        break
    return '\n'.join(lines[start:])



def _coerce_raw(raw_data) -> tuple:
    """统一原始邮件的文本与字节表示"""
    if isinstance(raw_data, bytes):
        raw_bytes = raw_data
        raw_text = raw_bytes.decode('latin-1', errors='replace')
        return raw_text, raw_bytes

    raw_text = raw_data or ''
    try:
        raw_bytes = raw_text.encode('latin-1', errors='replace')
    except Exception:
        raw_bytes = raw_text.encode('utf-8', errors='replace')
    return raw_text, raw_bytes



def parse_mail(raw_data, save_attachments_dir: str = None) -> dict:
    """
    解析原始邮件内容，返回结构化字典

    返回字典结构:
        {
            'from'        : '发件人名称 <地址>',
            'from_addr'   : '发件人邮箱地址',
            'to'          : '收件人',
            'subject'     : '主题（已解码中文）',
            'date'        : '日期字符串',
            'body'        : '纯文本正文（兼容旧字段）',
            'text_body'   : '纯文本正文',
            'html_body'   : 'HTML 正文',
            'attachments' : [...],
            'inline_parts': [...],
            'raw'         : '原始字符串（供调试）',
            'raw_bytes'   : b'原始邮件字节'
        }
    """
    raw_text, raw_bytes = _coerce_raw(raw_data)
    cleaned_text = _preprocess_raw_text(raw_text)
    cleaned_bytes = cleaned_text.encode('latin-1', errors='replace')

    try:
        msg = email.message_from_bytes(cleaned_bytes, policy=policy.default)
    except Exception as e:
        logger.error(f'[Parser] 邮件解析失败: {e}')
        return {
            'from': '',
            'from_addr': '',
            'to': '',
            'subject': '（解析失败）',
            'date': '',
            'body': raw_text,
            'text_body': raw_text,
            'html_body': '',
            'attachments': [],
            'inline_parts': [],
            'raw': raw_text,
            'raw_bytes': raw_bytes,
        }

    subject = _decode_str(str(msg.get('Subject', '')))
    from_raw = _decode_str(str(msg.get('From', '')))
    to_raw = _decode_str(str(msg.get('To', '')))
    date_raw = str(msg.get('Date', ''))

    _, from_addr = parseaddr(from_raw)

    try:
        date_str = parsedate_to_datetime(date_raw).strftime('%Y-%m-%d %H:%M')
    except Exception:
        date_str = date_raw

    text_body, html_body = _extract_bodies(msg)
    attachments, inline_parts = _extract_parts(msg, save_dir=save_attachments_dir)

    result = {
        'from': from_raw,
        'from_addr': from_addr,
        'to': to_raw,
        'subject': subject,
        'date': date_str,
        'body': text_body,
        'text_body': text_body,
        'html_body': html_body,
        'attachments': attachments,
        'inline_parts': inline_parts,
        'raw': raw_text,
        'raw_bytes': raw_bytes,
    }

    logger.info(f'[Parser] 解析完成 | 发件人: {from_addr} | 主题: {subject}')
    return result
