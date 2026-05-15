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
│   ├── compose_window.py      # 写信窗口 ✅
│   └── mail_preview.py        # HTML 正文预览与 cid 图片映射
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

本项目绝大多数依赖为 Python 内置标准库，需要额外安装以下包：

```bash
pip install pillow tkinterweb
```

> 若安装较慢，可使用国内镜像：
> ```bash
> pip install pillow tkinterweb -i https://pypi.tuna.tsinghua.edu.cn/simple
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
- 初始化 `inbox`、`sent_mails`、`accounts`、`mail_parts` 数据表
- 自动补齐 HTML 预览所需的数据库字段
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

### `core/mail_parser.py` — 邮件解析模块

当前支持：
- 解析纯文本邮件与 HTML 邮件
- 保留 `text_body` 和 `html_body`
- 提取普通附件与 `cid:` 内嵌资源
- 为 GUI 预览层提供 HTML 和图片资源基础数据

### `gui/mail_preview.py` — HTML 预览组件

负责：
- 在 Tkinter 中嵌入 HTML 视图
- 将 `cid:` 图片重写为本地缓存资源
- 在 HTML 不可用时回退到纯文本正文

---

## 测试说明

基础运行验证：

```bash
python main.py
```

建议手工验证以下场景：
- 纯文本邮件是否正常显示
- HTML 邮件排版是否正常
- 含 `cid:` 内嵌图片的邮件是否能显示图片
- 含图片附件的邮件是否能在预览区底部展示
- 旧数据库中的历史邮件是否仍能回退显示正文
