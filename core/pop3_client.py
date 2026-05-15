# core/pop3_client.py
# 成员B负责实现 — POP3 收信模块
# 使用原生 socket + ssl 实现，不依赖 poplib

import socket
import ssl

from utils.logger import logger


class POP3Client:
    def __init__(self, host='pop.qq.com', port=995):
        self.host = host
        self.port = port
        self.sock = None

    # ------------------------------------------------------------------ #
    #  底层收发
    # ------------------------------------------------------------------ #

    def _send(self, cmd: str):
        """发送一条 POP3 命令（自动追加 CRLF）"""
        raw = (cmd + '\r\n').encode('utf-8')
        self.sock.sendall(raw)
        logger.debug(f'>>> {cmd}')

    def _recv_line(self) -> str:
        """接收服务器一行响应（以 CRLF 结尾）"""
        data = b''
        while not data.endswith(b'\r\n'):
            byte = self.sock.recv(1)
            if not byte:
                break
            data += byte
        resp = data.decode('latin-1', errors='replace').rstrip('\r\n')
        logger.debug(f'<<< {resp}')
        return resp

    def _recv_multiline(self) -> str:
        """
        接收多行响应，直到遇到单独一行 '.'
        用于 LIST、RETR 等返回多行数据的命令
        """
        lines = []
        while True:
            line = self._recv_line()
            if line == '.':
                break
            if line.startswith('..'):
                line = line[1:]
            lines.append(line)
        return '\r\n'.join(lines)

    # ------------------------------------------------------------------ #
    #  连接与断开
    # ------------------------------------------------------------------ #

    def connect(self):
        """建立 TCP + SSL 连接，读取服务器欢迎信息"""
        logger.info(f'[POP3] 连接 {self.host}:{self.port}')
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(15)
        context = ssl.create_default_context()
        self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)
        self.sock.connect((self.host, self.port))
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise ConnectionError(f'POP3 连接失败: {resp}')
        logger.info('[POP3] 连接成功')

    def quit(self):
        """
        发送 QUIT 并关闭连接
        QUIT 后服务器才真正执行 DELE 标记的删除操作
        """
        try:
            self._send('QUIT')
            self._recv_line()
        finally:
            if self.sock:
                self.sock.close()
                self.sock = None
        logger.info('[POP3] 连接已关闭')

    # ------------------------------------------------------------------ #
    #  认证
    # ------------------------------------------------------------------ #

    def login(self, username: str, password: str):
        """
        USER / PASS 认证
        username: 完整邮箱地址，如 xxx@qq.com
        password: 授权码（不是登录密码）
        """
        self._send(f'USER {username}')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise PermissionError(f'USER 失败: {resp}')

        self._send(f'PASS {password}')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise PermissionError(f'PASS 失败: {resp}\n请确认授权码是否正确')

        logger.info(f'[POP3] 认证成功: {username}')

    # ------------------------------------------------------------------ #
    #  邮箱状态
    # ------------------------------------------------------------------ #

    def stat(self) -> tuple:
        """
        STAT 命令：返回 (邮件数量, 总字节数)
        例：+OK 10 50000 → (10, 50000)
        """
        self._send('STAT')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'STAT 失败: {resp}')
        parts = resp.split()
        count = int(parts[1])
        size = int(parts[2])
        logger.info(f'[POP3] 共 {count} 封邮件，总大小 {size} 字节')
        return count, size

    # ------------------------------------------------------------------ #
    #  邮件列表
    # ------------------------------------------------------------------ #

    def list_mails(self) -> dict:
        """
        LIST 命令：返回 {邮件编号(int): 字节大小(int)} 字典
        编号从 1 开始
        """
        self._send('LIST')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'LIST 失败: {resp}')
        content = self._recv_multiline()
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if line:
                parts = line.split()
                result[int(parts[0])] = int(parts[1])
        logger.info(f'[POP3] 获取邮件列表，共 {len(result)} 封')
        return result

    def uidl(self) -> dict:
        """
        UIDL 命令：返回 {邮件编号: 唯一ID字符串} 字典
        用于增量收信时判断邮件是否已下载过
        """
        self._send('UIDL')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'UIDL 失败: {resp}')
        content = self._recv_multiline()
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if line:
                parts = line.split()
                result[int(parts[0])] = parts[1]
        return result

    # ------------------------------------------------------------------ #
    #  下载邮件
    # ------------------------------------------------------------------ #

    def retrieve_mail(self, index: int) -> str:
        """
        RETR 命令：下载第 index 封邮件的完整原始内容
        返回符合 RFC 2822 格式的原始邮件字符串
        """
        self._send(f'RETR {index}')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'RETR {index} 失败: {resp}')
        raw = self._recv_multiline()
        logger.info(f'[POP3] 下载邮件 #{index}，大小 {len(raw)} 字节')
        return raw

    def top(self, index: int, lines: int = 0) -> str:
        """
        TOP 命令：只下载邮件头部（不下载正文），速度更快
        lines=0 表示只要头部，lines=N 表示头部+前N行正文
        可用于快速显示邮件列表（主题、发件人）
        """
        self._send(f'TOP {index} {lines}')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'TOP {index} 失败: {resp}')
        return self._recv_multiline()

    # ------------------------------------------------------------------ #
    #  删除邮件
    # ------------------------------------------------------------------ #

    def delete_mail(self, index: int):
        """
        DELE 命令：标记第 index 封邮件为删除
        注意：标记后在 QUIT 之前可用 RSET 撤销，QUIT 后才真正删除
        """
        self._send(f'DELE {index}')
        resp = self._recv_line()
        if not resp.startswith('+OK'):
            raise Exception(f'DELE {index} 失败: {resp}')
        logger.info(f'[POP3] 标记删除邮件 #{index}')

    def reset(self):
        """RSET 命令：撤销本次会话所有 DELE 标记"""
        self._send('RSET')
        resp = self._recv_line()
        logger.info(f'[POP3] 撤销删除标记: {resp}')

    # ------------------------------------------------------------------ #
    #  一步完成：连接 → 认证 → 收信 → 断开
    # ------------------------------------------------------------------ #

    def fetch_all(self, username: str, password: str, max_count: int = 20) -> list:
        """
        对外暴露的简便接口，自动完成完整收信流程。

        参数:
            username  : 邮箱地址
            password  : 授权码
            max_count : 最多下载最新 N 封邮件，默认 20

        返回:
            list of dict，每封邮件为一个字典，
            字典结构见 mail_parser.parse_mail() 的返回值
        """
        from core.mail_parser import parse_mail

        results = []
        try:
            self.connect()
            self.login(username, password)

            mail_list = self.list_mails()
            total = len(mail_list)

            try:
                uid_map = self.uidl()
            except Exception:
                uid_map = {}

            existing_uids = set()
            try:
                from db.database import get_all_uids
                existing_uids = get_all_uids()
            except Exception:
                pass

            indices = sorted(mail_list.keys(), reverse=True)[:max_count]
            new_indices = [
                idx for idx in indices
                if uid_map.get(idx, f'__no_uid_{idx}') not in existing_uids
            ]

            logger.info(f'[POP3] 服务器共 {total} 封，本次下载 {len(new_indices)} 封新邮件')

            for idx in new_indices:
                try:
                    raw = self.retrieve_mail(idx)
                    parsed = parse_mail(raw)
                    parsed['_index'] = idx
                    parsed['_uid'] = uid_map.get(idx, '')
                    results.append(parsed)
                except Exception as e:
                    logger.warning(f'[POP3] 解析邮件 #{idx} 失败: {e}')

            logger.info(f'[POP3] 共收取 {len(results)} 封新邮件')
        finally:
            self.quit()

        return results
