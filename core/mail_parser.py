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
CHARSET_FALLBACKS = ('utf-8', 'gb18030', 'gbk', 'gb2312', 'big5', 'latin-1')


def _decode_bytes(data: bytes, charsets) -> str:
    """按候选编码列表解码字节，最后使用替换策略兜底"""
    if data is None:
        return ''

    candidates = []
    for charset in charsets:
        if charset and charset not in candidates:
            candidates.append(charset)
    for charset in CHARSET_FALLBACKS:
        if charset not in candidates:
            candidates.append(charset)

    for charset in candidates:
        try:
            return data.decode(charset, errors='strict')
        except (LookupError, UnicodeDecodeError):
            continue

    for charset in candidates:
        try:
            return data.decode(charset, errors='replace')
        except LookupError:
            continue

    return data.decode('utf-8', errors='replace')



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
            result.append(_decode_bytes(part, [charset]))
        else:
            result.append(part)
    return ''.join(result)



def _decode_part(part) -> str:
    """安全解码一个 MIME part 的 payload，尝试多种编码"""
    raw_bytes = part.get_payload(decode=True)
    if raw_bytes is None:
        return ''
    charset = part.get_content_charset()
    return _decode_bytes(raw_bytes, [charset])



def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本内容，并处理 JS 风格 \\uXXXX Unicode 转义"""
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?(p|div|tr|li|ul|ol|table|tbody|thead|h[1-6])[^>]*>', '\n', html, flags=re.IGNORECASE)
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
            decoded = _decode_bytes(payload, [msg.get_content_charset()])
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
    """清理前导噪声并兼容折叠头字段，仅在 fallback 场景使用"""
    primary_hdr = re.compile(
        r'^(Content-Type|MIME-Version|From|To|Subject|Date|Content-Transfer-Encoding)\s*:',
        re.IGNORECASE,
    )
    generic_hdr = re.compile(r'^[A-Za-z][\w\-]*\s*:\s*.*$', re.ASCII)
    lines = raw_text.replace('\r\n', '\n').split('\n')

    def is_continuation_candidate(prev_line: str, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if generic_hdr.match(line):
            return False
        if stripped.startswith('=?'):
            return True
        if stripped.startswith(('boundary=', 'charset=', 'name=', 'filename=')):
            return True
        if prev_line.rstrip().endswith(';'):
            return True
        return False

    best_idx = None
    best_score = -1

    for idx, line in enumerate(lines):
        if not primary_hdr.match(line):
            continue

        header_count = 0
        blank_found = False
        jammed_headers = False
        normalized_block = []
        prev_header_line = ''

        for follow in lines[idx:idx + 40]:
            if not follow.strip():
                blank_found = True
                break

            if re.match(r'^\s+', follow):
                normalized_block.append(follow)
                continue

            if generic_hdr.match(follow):
                if len(re.findall(r'[A-Za-z][\w\-]*\s*:', follow)) >= 2:
                    jammed_headers = True
                    break
                normalized_block.append(follow)
                prev_header_line = follow
                header_count += 1
                continue

            if prev_header_line and is_continuation_candidate(prev_header_line, follow):
                normalized_block.append(' ' + follow.lstrip())
                continue

            break

        if not blank_found or header_count < 4 or jammed_headers:
            continue

        score = header_count
        if re.match(r'^(From|To|Subject)\s*:', line, re.IGNORECASE):
            score += 2
        if any(re.match(r'^Content-Type\s*:\s*multipart/', item, re.IGNORECASE) for item in normalized_block):
            score += 1

        if score > best_score:
            best_idx = idx
            best_score = score

    if best_idx is None:
        return '\n'.join(lines)

    normalized_lines = lines[:]
    in_headers = True
    prev_header_line = ''
    for pos in range(best_idx, len(normalized_lines)):
        current = normalized_lines[pos]
        if not current.strip():
            in_headers = True
            prev_header_line = ''
            continue
        if re.match(r'^--', current):
            in_headers = True
            prev_header_line = ''
            continue
        if not in_headers:
            continue
        if re.match(r'^\s+', current):
            continue
        if generic_hdr.match(current):
            prev_header_line = current
            continue
        if prev_header_line and is_continuation_candidate(prev_header_line, current):
            normalized_lines[pos] = ' ' + current.lstrip()
            continue
        in_headers = False

    cleaned = '\n'.join(normalized_lines[best_idx:])
    if '\n\n' not in cleaned:
        cleaned = cleaned.replace('\n--', '\n\n--', 1)
    return cleaned



def _coerce_raw(raw_data) -> tuple:
    """统一原始邮件的字节与调试文本表示，优先保留原始字节"""
    if isinstance(raw_data, bytes):
        raw_bytes = raw_data
    else:
        raw_text = raw_data or ''
        try:
            raw_bytes = raw_text.encode('latin-1', errors='strict')
        except UnicodeEncodeError:
            raw_bytes = raw_text.encode('utf-8', errors='replace')
    raw_text = raw_bytes.decode('latin-1', errors='replace')
    return raw_bytes, raw_text



def _message_looks_broken(msg, text_body: str, html_body: str) -> bool:
    """判断解析结果是否明显异常，用于触发 fallback"""
    preview = (text_body or html_body or '').strip()

    if not msg.get('Subject') and not msg.get('From'):
        return True
    if msg.get_content_type() == 'text/plain' and 'multipart/' in preview[:200]:
        return True
    if not preview:
        return False

    suspicious_tokens = ('Content-Type:', 'MIME-Version:', 'Received:', 'Content-Transfer-Encoding:')
    if any(token in preview[:200] for token in suspicious_tokens):
        return True
    return False



def _parse_message_from_bytes(raw_bytes: bytes, raw_text: str, use_fallback: bool = False):
    """从字节构建 email.message 对象，必要时对遗留文本进行保守 fallback 预处理"""
    if use_fallback:
        cleaned_text = _preprocess_raw_text(raw_text)
        parse_bytes = cleaned_text.encode('latin-1', errors='replace')
    else:
        parse_bytes = raw_bytes
    return email.message_from_bytes(parse_bytes, policy=policy.default)



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
    raw_bytes, raw_text = _coerce_raw(raw_data)

    try:
        msg = _parse_message_from_bytes(raw_bytes, raw_text, use_fallback=False)
        text_body, html_body = _extract_bodies(msg)
        if _message_looks_broken(msg, text_body, html_body):
            msg = _parse_message_from_bytes(raw_bytes, raw_text, use_fallback=True)
            text_body, html_body = _extract_bodies(msg)
    except Exception:
        try:
            msg = _parse_message_from_bytes(raw_bytes, raw_text, use_fallback=True)
            text_body, html_body = _extract_bodies(msg)
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
