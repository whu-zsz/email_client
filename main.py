# main.py
import tkinter as tk
from db.database import init_db
from gui.login_window import LoginWindow

def main():
    # 初始化数据库
    init_db()

    # 启动 GUI
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()

if __name__ == '__main__':
    main()