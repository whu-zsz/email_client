# utils/theme.py
# 集中管理 UI 视觉参数

import tkinter as tk
from tkinter import ttk

# ------------------------------------------------------------------ #
#  配色
# ------------------------------------------------------------------ #

BG          = '#f5f5f0'
CARD        = '#ffffff'
HEADER      = '#2c2c2a'
DIVIDER     = '#d3d1c7'
DIVIDER_DK  = '#c3c1b7'
TEXT        = '#2c2c2a'
TEXT_SEC    = '#5f5e5a'
TEXT_MUTED  = '#888780'
TEXT_HINT   = '#b4b2a9'
ACCENT      = '#1D9E75'
ACCENT_HOVER= '#168a63'
ERROR       = '#E24B4A'
HOVER       = '#e8e8e4'
HEADER_HOVER= '#3d3d3b'
SELECT_BG   = '#E8F0FE'
SELECT_FG   = '#1a73e8'
UNREAD_DOT  = '#378ADD'

# ------------------------------------------------------------------ #
#  字体
# ------------------------------------------------------------------ #

FAMILY   = 'PingFang SC'
FALLBACK = 'Microsoft YaHei'
BODY     = (FAMILY, 11)
HEADING  = (FAMILY, 13, 'bold')
SMALL    = (FAMILY, 9)
TINY     = (FAMILY, 8)

# ------------------------------------------------------------------ #
#  间距
# ------------------------------------------------------------------ #

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 20


# ------------------------------------------------------------------ #
#  ttk 样式配置
# ------------------------------------------------------------------ #

def setup_styles():
    """初始化 ttk 控件样式，应在 Tk() 创建后、主窗口加载前调用"""
    style = ttk.Style()

    # --- Treeview ---
    style.configure(
        'Mail.Treeview',
        rowheight=36,
        font=BODY,
        background=CARD,
        foreground=TEXT,
        fieldbackground=CARD,
        borderwidth=0,
        relief='flat',
    )
    style.map(
        'Mail.Treeview',
        background=[('selected', SELECT_BG)],
        foreground=[('selected', SELECT_FG)],
    )
    style.configure(
        'Mail.Treeview.Heading',
        font=(FAMILY, 10, 'bold'),
        background='#f0f0ec',
        foreground=TEXT_SEC,
        relief='flat',
        borderwidth=0,
    )
    style.map(
        'Mail.Treeview.Heading',
        background=[('active', HOVER)],
    )

    # --- Scrollbar ---
    style.configure(
        'Mail.Vertical.TScrollbar',
        width=6,
        troughcolor=BG,
        background=TEXT_HINT,
        relief='flat',
        borderwidth=0,
    )
    style.map(
        'Mail.Vertical.TScrollbar',
        background=[('active', TEXT_MUTED)],
    )

    # --- Combobox ---
    style.configure(
        'Mail.TCombobox',
        font=BODY,
        padding=4,
    )
