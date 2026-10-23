"""Sao lưu, so sánh và khôi phục cấu hình (yêu cầu chức năng số 4)."""

import difflib
from datetime import datetime
from pathlib import Path

from netauto.core.logger import audit, get_logger

# Những dòng có trong file sao lưu nhưng không phải lệnh cấu hình,
# cần bỏ đi trước khi gửi lại lên thiết bị lúc khôi phục.
SKIP_PREFIXES = ("!", "#", "Building configuration", "Current configuration")


class BackupManager:
    def __init__(self, backup_dir="data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()

    def _device_dir(self, device_name):
        folder = self.backup_dir / device_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def backup(self, device, user="system"):
        """Lấy running-config của thiết bị và lưu ra file
        <tên thiết bị>_<thời gian>.cfg. Trả về đường dẫn file."""
        result = device.execute_task(device.get_running_config, user=user)
        if not result["success"]:
            raise RuntimeError(f"Sao lưu thất bại cho {device.name}: {result['error']}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self._device_dir(device.name) / f"{device.name}_{timestamp}.cfg"
        file_path.write_text(result["data"], encoding="utf-8")
        self.logger.info("Đã sao lưu %s -> %s", device.name, file_path)
        return file_path

    def list_backups(self, device_name):
        return sorted(self._device_dir(device_name).glob("*.cfg"))

    def diff(self, device_name, older=None, newer=None):
        """So sánh 2 bản sao lưu (mặc định là 2 bản gần nhất) để phát hiện
        cấu hình bị thay đổi."""
        backups = self.list_backups(device_name)
        if older is None or newer is None:
            if len(backups) < 2:
                return "Chưa đủ bản sao lưu để so sánh."
            older, newer = backups[-2], backups[-1]

        diff_lines = difflib.unified_diff(
            Path(older).read_text(encoding="utf-8").splitlines(),
            Path(newer).read_text(encoding="utf-8").splitlines(),
            fromfile=str(older),
            tofile=str(newer),
            lineterm="",
        )
        return "\n".join(diff_lines) or "Không có khác biệt."

    @staticmethod
    def read_config_lines(backup_file):
        """Đọc file sao lưu, bỏ dòng trống, dòng chú thích và dòng tiêu đề."""
        lines = []
        for line in Path(backup_file).read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text == "end" or text.startswith(SKIP_PREFIXES):
                continue
            lines.append(line)
        return lines

    def restore(self, device, backup_file, user="system"):
        """Khôi phục: gửi lại cấu hình trong file sao lưu lên thiết bị.

        Lưu ý: cách này ghi đè lại các dòng cũ nhưng không xóa được những
        dòng mới được thêm vào sau thời điểm sao lưu.
        """
        lines = self.read_config_lines(backup_file)
        # check_errors=False: khi khôi phục, một dòng lỗi không được làm dừng
        # cả quá trình, các dòng còn lại vẫn phải được gửi lên thiết bị.
        result = device.execute_task(device.push_config, lines, user=user, check_errors=False)
        audit("restore", device.name, user, "OK" if result["success"] else "FAILED", str(backup_file))
        return result
