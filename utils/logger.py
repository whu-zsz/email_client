# utils/logger.py
import logging
import os
import sys

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'app.log')

# 控制台编码可能与日志文件编码不同，终端乱码不一定代表 GUI/数据库内容已损坏。
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger('EmailClient')