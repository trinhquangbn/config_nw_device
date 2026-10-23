"""Các đường dẫn/cấu hình mặc định dùng chung cho toàn chương trình.

Đọc từ biến môi trường nếu có, không thì dùng giá trị mặc định. Gom về
một chỗ để không phải lặp lại các đường dẫn này ở nhiều file khác nhau.
"""

import os

INVENTORY_PATH = os.getenv("NETAUTO_INVENTORY", "config/inventory.yaml")
TEMPLATES_DIR = os.getenv("NETAUTO_TEMPLATES_DIR", "templates_config")
VARS_DIR = os.getenv("NETAUTO_VARS_DIR", "variables")  # các file JSON biến mẫu cho template
BACKUP_DIR = os.getenv("NETAUTO_BACKUP_DIR", "data/backups")
REPORT_DIR = os.getenv("NETAUTO_REPORT_DIR", "data/reports")
MAX_WORKERS = int(os.getenv("NETAUTO_MAX_WORKERS", "8"))
