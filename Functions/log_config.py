import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file_path = os.path.join(LOG_DIR, "ai_web_ide.log")


def setup_logging():
    """
    設定一個集中式的日誌記錄器，將日誌寫入一個會自動輪替的檔案中。
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 避免重複添加 handlers
    if any(isinstance(h, RotatingFileHandler) and h.baseFilename == log_file_path for h in logger.handlers):
        return

    # 建立一個輪替檔案處理器
    # 當日誌檔案達到 10MB 時會輪替，並保留 5 個舊的日誌檔案。
    handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')

    # 建立格式化器並為處理器設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
    handler.setFormatter(formatter)

    # 將處理器添加到根日誌記錄器
    logger.addHandler(handler)


def get_logger(name):
    """
    獲取一個指定名稱的 logger 實例。
    """
    return logging.getLogger(name)
