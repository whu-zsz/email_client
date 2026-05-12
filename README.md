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
- [开发分工](#开发分工)

---

## 项目结构

```
email_client/
│
├── main.py                    # 程序入口，启动 GUI 并初始化数据库
├── config.ini                 # 邮箱服务器与账户配置（本地使用，勿提交 Git）
├── README.md                  # 项目说明文档
├── .gitignore                 # Git 忽略规则
│
├── core/                      # 核心协议层
│   ├── __init__.py
│   ├── smtp_client.py         # SMTP 发送模块（基于 socket 实现）
│   ├── pop3_client.py         # POP3 收信模块（基于 socket 实现）
│   └── mail_parser.py         # 邮件原始内容解析（头部/正文/附件）
│
├── gui/                       # 图形界面层
│   ├── __init__.py
│   ├── login_window.py        # 登录窗口
│   ├── main_window.py         # 主窗口（收件箱/已发送列表）
│   └── compose_window.py      # 写信窗口
│
├── db/                        # 数据库层
│   ├── __init__.py
│   └── database.py            # 数据库初始化、增删查操作封装
│
├── utils/                     # 工具层
│   ├── __init__.py
│   └── logger.py              # 统一日志记录
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

复制配置文件模板并填入你的邮箱信息（见下一节）：

```bash
# 直接编辑 config.ini
```

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

在项目根目录下运行：

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

### `core/smtp_client.py` — SMTP 发送模块

使用原生 `socket` + `ssl` 实现 SMTP 协议，不依赖任何第三方邮件库。

主要功能：
- 建立 TCP + SSL 加密连接
- 完成 EHLO 握手与 BASE64 登录认证
- 构造符合 RFC 2822 标准的 MIME 格式邮件
- 支持中文主题/正文（UTF-8 编码）
- 支持附件发送

---

### `core/pop3_client.py` — POP3 收信模块

使用原生 `socket` + `ssl` 实现 POP3 协议，不依赖任何第三方邮件库。

主要功能：
- 建立 TCP + SSL 加密连接
- USER / PASS 登录认证
- STAT / LIST 获取邮件数量与列表
- RETR 下载指定邮件原始内容
- DELE 标记删除邮件（QUIT 后生效）

---

### `core/mail_parser.py` — 邮件解析

解析从 POP3 服务器获取的原始邮件内容（符合 RFC 2822 格式），提取结构化信息。

主要功能：
- 解析邮件头：From / To / Subject / Date
- 解码中文主题（Base64 / Quoted-Printable）
- 提取纯文本正文
- 提取附件并保存到本地

---

### `gui/login_window.py` — 登录窗口

程序启动后显示的第一个界面，输入邮箱账号和授权码，验证成功后跳转主窗口。

---

### `gui/main_window.py` — 主窗口

三栏布局的核心操作界面：
- **左栏**：文件夹树（收件箱 / 已发送 / 草稿箱）
- **中栏**：邮件列表，显示发件人、主题、时间
- **右栏**：邮件正文预览区

---

### `gui/compose_window.py` — 写信窗口

点击「写信」按钮弹出，包含收件人、主题、正文输入框及发送按钮，调用 `SMTPClient` 完成发送。

---

### `db/database.py` — 数据库模块

封装所有 SQLite 数据库操作，包含三张表：

| 表名 | 用途 |
|------|------|
| `inbox` | 存储已接收的邮件（含已读状态） |
| `sent_mails` | 存储已发送的邮件记录 |
| `accounts` | 存储账户信息（邮箱、授权码、服务器配置） |

---

### `utils/logger.py` — 日志模块

统一的日志记录工具，同时输出到终端和 `data/app.log` 文件，方便调试和排查问题。

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

## 开发分工

| 成员 | 负责模块 | 主要文件 |
|------|---------|---------|
| 成员A | SMTP 发送 | `core/smtp_client.py` |
| 成员B | POP3 收信 + 邮件解析 | `core/pop3_client.py` `core/mail_parser.py` |
| 成员C | GUI 界面 | `gui/login_window.py` `gui/main_window.py` `gui/compose_window.py` |
| 成员D | 数据库 + 系统集成 + 报告 | `db/database.py` `main.py` `config.ini` |
