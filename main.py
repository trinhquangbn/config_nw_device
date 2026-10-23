"""Điểm khởi chạy chương trình từ thư mục gốc của dự án.

Ví dụ:
    python main.py inventory-list
    python main.py push --group access --template vlan.j2 --vars sample_vars.json --dry-run
"""

import sys
from pathlib import Path

# Thêm thư mục src vào đường dẫn tìm module để import được gói netauto.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from netauto.cli import main  # noqa: E402  (phải import sau khi thêm đường dẫn)

if __name__ == "__main__":
    main()
