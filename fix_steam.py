# fix_steam.py — 放项目根目录运行：python fix_steam.py
# 旧版 Steam 邮件专项修复入口，现已统一收敛到 fix_inbox.py

from fix_inbox import main

if __name__ == '__main__':
    print('提示：fix_steam.py 已收敛为通用修复流程，将调用 fix_inbox.py')
    main()
