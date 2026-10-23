"""Chạy tác vụ trên nhiều thiết bị cùng lúc (yêu cầu chức năng số 2, 3, 5).

Mỗi thiết bị được xử lý trong một luồng (thread) riêng nhờ
ThreadPoolExecutor, nên không phải chờ lần lượt từng thiết bị. Nếu một
thiết bị bị lỗi thì chỉ ghi nhận lỗi của thiết bị đó, các thiết bị khác
vẫn chạy bình thường.
"""

from concurrent.futures import ThreadPoolExecutor

from netauto.core.backup_manager import BackupManager
from netauto.core.logger import audit, get_logger


class BatchOperator:
    def __init__(self, max_workers=8, backup_manager=None):
        self.max_workers = max_workers
        self.backup_manager = backup_manager or BackupManager()
        self.logger = get_logger()

    def _run_parallel(self, func, devices, *args):
        """Gọi func(device, *args) cho từng thiết bị, mỗi thiết bị một luồng.
        Trả về danh sách kết quả theo đúng thứ tự danh sách thiết bị."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(func, device, *args) for device in devices]
            return [future.result() for future in futures]

    # ------------------------------------------------------------------ #
    # Các tác vụ hàng loạt
    # ------------------------------------------------------------------ #
    def check_all(self, devices, user="system"):
        """Kiểm tra kết nối tới từng thiết bị."""
        return self._run_parallel(self._check_one, devices, user)

    def collect_facts(self, devices, user="system"):
        """Thu thập thông tin từ nhiều thiết bị."""
        return self._run_parallel(self._collect_one, devices, user)

    def backup_all(self, devices, user="system"):
        """Sao lưu cấu hình của nhiều thiết bị."""
        return self._run_parallel(self._backup_one, devices, user)

    def push_batch(self, devices, config_lines, dry_run=True, auto_rollback=True, user="system"):
        """Áp cấu hình cho nhiều thiết bị.

        dry_run=True: chỉ trả về các lệnh sẽ được áp dụng, không kết nối tới
        thiết bị nào cả, để người dùng kiểm tra trước.
        """
        if dry_run:
            results = []
            for device in devices:
                results.append({"device": device.name, "host": device.host, "success": True,
                                "dry_run": True, "planned_lines": config_lines})
            return results
        return self._run_parallel(self._push_one, devices, config_lines, auto_rollback, user)

    # ------------------------------------------------------------------ #
    # Xử lý cho MỘT thiết bị (mỗi hàm chạy trong một luồng riêng)
    # ------------------------------------------------------------------ #
    def _check_one(self, device, user):
        return device.execute_task(device.is_alive, user=user)

    def _collect_one(self, device, user):
        return device.execute_task(device.get_facts, user=user)

    def _backup_one(self, device, user):
        result = {"device": device.name, "host": device.host}
        try:
            path = self.backup_manager.backup(device, user=user)
            result["success"] = True
            result["backup_file"] = str(path)
        except Exception as exc:
            result["success"] = False
            result["error"] = str(exc)
        return result

    def _push_one(self, device, config_lines, auto_rollback, user):
        # Bước 1: sao lưu cấu hình hiện tại để có thể rollback.
        try:
            pre_backup = self.backup_manager.backup(device, user=user)
        except Exception as exc:
            return {"device": device.name, "host": device.host, "success": False,
                    "error": f"Không sao lưu được trước khi cấu hình, hủy thao tác: {exc}"}

        # Bước 2: áp cấu hình mới.
        result = device.execute_task(device.push_config, config_lines, user=user)
        result["pre_backup"] = str(pre_backup)

        # Bước 3: nếu lỗi thì tự khôi phục về bản sao lưu ở bước 1.
        if not result["success"] and auto_rollback:
            self.logger.warning("Áp cấu hình lỗi trên %s, đang rollback về %s", device.name, pre_backup)
            rollback = self.backup_manager.restore(device, pre_backup, user=user)
            result["rolled_back"] = rollback["success"]
            audit("rollback", device.name, user, "OK" if rollback["success"] else "FAILED", str(pre_backup))

        return result
