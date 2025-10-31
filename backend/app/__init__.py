# 聊天内容智能分析平台 - 后端应用包
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    log_dir = Path(__file__).resolve().parent.parent
    file_handler = RotatingFileHandler(str(log_dir / "uvicorn.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)
    if root.level > logging.INFO:
        root.setLevel(logging.INFO)


configure_logging()

