"""Cấu hình logging dùng chung cho cả chương trình.

Ghi log ra 2 nơi: màn hình console và file logs/netauto.log, để sau này
xem lại được ai đã làm gì, trên thiết bị nào, kết quả ra sao.
"""

import logging
from pathlib import Path

_logger = None  # chỉ tạo logger 1 lần, các lần gọi sau dùng lại


def get_logger():
    """Trả về logger dùng chung cho toàn chương trình (tạo 1 lần duy nhất)."""
    global _logger
    if _logger is not None:
        return _logger

    Path("logs").mkdir(exist_ok=True)

    logger = logging.getLogger("netauto")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    file_handler = logging.FileHandler("logs/netauto.log", encoding="utf-8")
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    _logger = logger
    return _logger


def audit(action, device, user, result, detail=""):
    """Ghi 1 dòng log thao tác: ai làm gì, trên thiết bị nào, kết quả gì."""
    get_logger().info(
        "action=%s device=%s user=%s result=%s detail=%s",
        action, device, user, result, detail,
    )
