import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file_path = os.path.join(LOG_DIR, "ai_web_ide.log")


def setup_logging(log_to_file=True):
    """
    設定日誌記錄器，支援檔案模式或終端機模式。

    Args:
        log_to_file (bool): 
            True - 將日誌輸出到檔案 (預設)
            False - 將日誌輸出到終端機
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除現有的處理器以避免重複
    logger.handlers.clear()

    if log_to_file:
        # 檔案模式：將日誌寫入輪替檔案
        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        print(f"✓ 日誌模式：檔案輸出 - 日誌將儲存至 {log_file_path}")
    else:
        # 終端機模式：將日誌輸出到控制台
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        print("✓ 日誌模式：終端機輸出")


def get_logger(name):
    """
    獲取一個指定名稱的 logger 實例。
    """
    return logging.getLogger(name)
