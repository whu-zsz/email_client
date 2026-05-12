# utils/logger.py
import logging
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()   # 同时输出到终端
    ]
)

logger = logging.getLogger('EmailClient')