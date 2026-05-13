# 📧 邮件客户端系统

> 2026年计算机网络实践课设 · 基于 Socket 实现 SMTP / POP3 协议的桌面邮件客户端
>
> 语言：Python 3.x | GUI：tkinter | 数据库：SQLite

---

## 目录

- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [初始化项目](#初始化项目)
- [配置邮箱](#配置邮箱)
- [启动程序](#启动程序)
- [各模块说明](#各模块说明)
- [测试说明](#测试说明)
- [开发分工](#开发分工)
- [开发进度](#开发进度)

---

## 项目结构

```
email_client/
│
├── main.py                    # 程序入口，启动 GUI 并初始化数据库
├── test_smtp.py               # SMTP 发送模块独立测试脚本
├── test_pop3.py               # POP3 收信模块独立测试脚本
├── config.ini                 # 邮箱服务器与账户配置（本地使用，勿提交 Git）
├── README.md                  # 项目说明文档
├── .gitignore                 # Git 忽略规则
│
├── core/                      # 核心协议层
│   ├── __init__.py
│   ├── smtp_client.py         # SMTP 发送模块（基于 socket 实现）✅
│   ├── pop3_client.py         # POP3 收信模块（基于 socket 实现）✅
│   └── mail_parser.py         # 邮件原始内容解析（头部/正文/附件）✅
│
├── gui/                       # 图形界面层
│   ├── __init__.py
│   ├── login_window.py        # 登录窗口 ✅
│   ├── main_window.py         # 主窗口（收件箱/已发送列表）✅
│   └── compose_window.py      # 写信窗口 ✅
│
├── db/                        # 数据库层
│   ├── __init__.py
│   └── database.py            # 数据库初始化、增删查操作封装（成员D负责）
│
├── utils/                     # 工具层
│   ├── __init__.py
│   └── logger.py              # 统一日志记录 ✅
│
├── assets/                    # 静态资源
│   └── icon.png               # 应用图标
│
└── data/                      # 运行时自动生成，无需手动创建
    ├── mail.db                # SQLite 数据库文件
    └── app.log                # 运行日志
```

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.8 及以上 |
| 操作系统 | Windows 10 / 11 |
| 编辑器 | VSCode（推荐） |

检查 Python 版本：

```bash
python --version
```

---

## 初始化项目

### 1. 克隆或下载项目

```bash
git clone <仓库地址>
cd email_client
```

### 2. 安装依赖

本项目绝大多数依赖为 Python 内置标准库，只需额外安装一个包：

```bash
pip install pillow
```

> 若安装较慢，可使用国内镜像：
> ```bash
> pip install pillow -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

### 3. 配置邮箱信息

直接编辑项目根目录下的 `config.ini`（见下一节）。

---

## 配置邮箱

编辑项目根目录下的 `config.ini`：

```ini
[QQ]
smtp_host = smtp.qq.com
smtp_port = 465
pop3_host = pop.qq.com
pop3_port = 995

[163]
smtp_host = smtp.163.com
smtp_port = 465
pop3_host = pop.163.com
pop3_port = 995

[account]
email    = 你的邮箱@qq.com
password = 你的授权码
```

> ⚠️ **重要：密码处填写「授权码」，不是登录密码。**
>
> 获取授权码方式：
> - QQ邮箱：登录网页版 → 设置 → 账户 → 开启 SMTP/POP3 服务 → 生成授权码
> - 163邮箱：登录网页版 → 设置 → POP3/SMTP/IMAP → 开启服务 → 设置授权密码

---

## 启动程序

### 启动主程序

```bash
python main.py
```

首次启动时程序会自动完成以下操作：
- 在 `data/` 目录下创建 `mail.db` 数据库
- 初始化 `inbox`、`sent_mails`、`accounts` 三张数据表
- 弹出登录窗口

**预期终端输出：**

```
[DB] 数据库初始化完成
```

**预期界面：** 弹出登录窗口 ✅

---

## 各模块说明

### `main.py` — 程序入口

负责启动整个应用，调用数据库初始化，然后创建 tkinter 根窗口并加载登录界面。

---

### `config.ini` — 配置文件

存储邮件服务器地址、端口及账户授权码。**不要将此文件提交到 Git 仓库。**

---

### `core/smtp_client.py` — SMTP 发送模块 ✅

使用原生 `socket` + `ssl` 实现 SMTP 协议，不依赖任何第三方邮件库。

主要功能：
- 建立 TCP + SSL 加密连接（端口 465）
- 完成 EHLO 握手与 Base64 登录认证（AUTH LOGIN）
- 构造符合 RFC 2822 标准的 MIME 格式邮件
- 支持中文主题 / 正文（UTF-8 + Header 编码）
- 支持附件发送（MIMEBase + Base64 编码）
- 对外提供 `send()` 一步调用接口

核心类：`SMTPClient`

| 方法 | 说明 |
|------|------|
| `connect()` | 建立 TCP + SSL 连接 |
| `ehlo()` | EHLO 握手 |
| `auth_login(user, pwd)` | Base64 认证 |
| `send_mail(...)` | 执行 SMTP 发送命令序列 |
| `send(...)` | 一步完成全流程的简便接口 |
| `quit()` | 断开连接 |

---

### `core/pop3_client.py` — POP3 收信模块 ✅

使用原生 `socket` + `ssl` 实现 POP3 协议，不依赖任何第三方邮件库。

主要功能：
- 建立 TCP + SSL 加密连接（端口 995）
- USER / PASS 登录认证
- STAT 获取邮件数量与总大小
- LIST 获取全部邮件编号和大小
- UIDL 获取邮件唯一 ID（用于增量收信去重）
- RETR 下载指定邮件完整原始内容
- TOP 只下载邮件头部（快速预览，不下载正文）
- DELE 标记删除邮件（QUIT 后生效）
- RSET 撤销删除标记
- 对外提供 `fetch_all()` 一步收信接口

核心类：`POP3Client`

| 方法 | 说明 |
|------|------|
| `connect()` | 建立 TCP + SSL 连接 |
| `login(user, pwd)` | USER / PASS 认证 |
| `stat()` | 返回 (邮件数, 总字节数) |
| `list_mails()` | 返回 {编号: 大小} 字典 |
| `uidl()` | 返回 {编号: 唯一ID} 字典 |
| `retrieve_mail(idx)` | 下载第 idx 封原始邮件 |
| `top(idx, lines)` | 只下载邮件头部 |
| `delete_mail(idx)` | 标记删除 |
| `reset()` | 撤销所有删除标记 |
| `fetch_all(...)` | 一步完成连接→收信→解析→返回列表 |
| `quit()` | 断开连接 |

---

### `core/mail_parser.py` — 邮件解析模块 ✅

解析从 POP3 服务器获取的原始 RFC 2822 格式邮件，提取结构化信息。

主要功能：
- 解析邮件头：From / To / Subject / Date
- 解码中文主题和发件人（Base64 / Quoted-Printable）
- 优先提取纯文本正文，备用 HTML 自动去标签
- 提取所有附件，可选自动保存到本地目录
- 对外提供 `parse_mail()` 统一入口

对外接口：

```python
parse_mail(raw_data, save_attachments_dir=None) -> dict
# 返回结构：
{
    'from'        : '发件人名称 <地址>',
    'from_addr'   : '发件人邮箱地址',
    'to'          : '收件人',
    'subject'     : '主题（已解码中文）',
    'date'        : '2026-05-13 10:30',
    'body'        : '纯文本正文',
    'attachments' : [{'filename': '...', 'data': b'...', 'saved_path': '...'}],
    'raw'         : '原始字符串'
}
```

---

### `gui/login_window.py` — 登录窗口 ✅

程序启动后显示的第一个界面。

主要功能：
- QQ邮箱 / 163邮箱 / 自定义 下拉切换，自动填充服务器配置
- 显示 / 隐藏授权码切换
- 记住账号，下次启动自动填充（写入 `config.ini`）
- 后台线程验证登录（POP3 连接测试），界面不卡死
- 验证成功后隐藏登录窗口，打开主窗口

---

### `gui/main_window.py` — 主窗口 ✅

三栏布局的核心操作界面。

主要功能：
- 顶部工具栏：写信 / 收信 / 删除
- 左栏：收件箱 / 已发送 文件夹切换，当前文件夹高亮显示
- 中栏：邮件列表（主题 / 发件人 / 时间），已读粗体 / 未读普通字体区分，支持关键词搜索过滤
- 右栏：邮件正文预览，显示发件人、主题、时间、正文、附件信息
- 启动后自动在后台收取一次邮件
- 收信、删除均在后台线程执行，不阻塞界面

---

### `gui/compose_window.py` — 写信窗口 ✅

点击「写信」按钮弹出的模态窗口。

主要功能：
- 显示发件人（只读）、收件人、主题输入框
- 正文编辑区域（支持滚动）
- 多文件附件选择，底部显示已选附件名称
- 基本格式校验（收件人不为空、地址含 @）
- 主题为空时弹窗二次确认
- 后台线程发送，发送中禁用按钮防止重复点击
- 发送成功后自动写入已发送数据库并关闭窗口

---

### `db/database.py` — 数据库模块

封装所有 SQLite 数据库操作，包含三张表：

| 表名 | 用途 |
|------|------|
| `inbox` | 存储已接收的邮件（含已读状态） |
| `sent_mails` | 存储已发送的邮件记录 |
| `accounts` | 存储账户信息（邮箱、授权码、服务器配置） |

GUI 层调用的接口（由成员D实现）：

| 函数 | 说明 |
|------|------|
| `init_db()` | 初始化数据库表结构 |
| `insert_inbox(mail)` | 存入一封收到的邮件 |
| `insert_sent(mail)` | 存入一封已发邮件 |
| `get_inbox()` | 查询收件箱列表 |
| `get_sent()` | 查询已发送列表 |
| `delete_mail(id)` | 按 id 删除一封邮件 |
| `mark_as_read(id)` | 标记邮件为已读 |

---

### `utils/logger.py` — 日志模块 ✅

统一的日志记录工具，同时输出到终端和 `data/app.log` 文件，方便调试和排查问题。

所有模块通过以下方式使用：

```python
from utils.logger import logger
logger.info('消息')
logger.warning('警告')
logger.error('错误')
```

---

### `assets/` — 静态资源

存放应用图标等图片资源，供 GUI 界面使用。

---

### `data/` — 运行时数据（自动生成）

| 文件 | 说明 |
|------|------|
| `mail.db` | SQLite 数据库，存储所有邮件数据 |
| `app.log` | 运行日志，记录发送/接收/错误信息 |

> 此目录由程序自动创建，无需手动操作，且已加入 `.gitignore`。

---

## 测试说明

### 测试 SMTP 发送模块

```bash
python test_smtp.py
```

修改脚本顶部的 `MY_EMAIL` 和 `MY_PASSWD` 后运行：

| 测试 | 内容 |
|------|------|
| 测试1 | 发送纯文本邮件 |
| 测试2 | 发送中文主题与正文邮件 |
| 测试3 | 发送带附件邮件 |

### 测试 POP3 收信模块

```bash
python test_pop3.py
```

修改脚本顶部的 `MY_EMAIL` 和 `MY_PASSWD` 后运行：

| 测试 | 内容 |
|------|------|
| 测试1 | SSL 连接与登录认证 |
| 测试2 | 获取邮件列表（LIST 命令） |
| 测试3 | 下载并解析最新一封邮件（RETR + 解析）|
| 测试4 | 批量收取最新 5 封邮件（fetch_all）|
| 测试5 | 只下载邮件头部快速预览（TOP 命令）|

---

## 开发分工

| 成员 | 负责模块 | 主要文件 |
|------|---------|---------|
| 成员A | SMTP 发送 | `core/smtp_client.py` |
| 成员B | POP3 收信 + 邮件解析 | `core/pop3_client.py` `core/mail_parser.py` |
| 成员C | GUI 界面 | `gui/login_window.py` `gui/main_window.py` `gui/compose_window.py` |
| 成员D | 数据库 + 系统集成 + 报告 | `db/database.py` `main.py` `config.ini` |

---

## 开发进度

| 模块 | 状态 |
|------|------|
| 项目框架搭建 | ✅ 完成 |
| `core/smtp_client.py` | ✅ 完成，测试通过 |
| `core/pop3_client.py` | ✅ 完成，测试通过 |
| `core/mail_parser.py` | ✅ 完成，测试通过 |
| `gui/login_window.py` | ✅ 完成 |
| `gui/main_window.py` | ✅ 完成 |
| `gui/compose_window.py` | ✅ 完成 |
| `db/database.py` | 🔨 进行中（成员D） |
| 模块联调 | ⏳ 待数据库完成后进行 |
| 实验报告 | ⏳ 待联调完成后撰写 |