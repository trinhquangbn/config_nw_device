"""Quản lý kho thiết bị (Inventory) - yêu cầu chức năng số 1.

Đọc danh sách thiết bị từ file YAML/JSON/CSV bên ngoài (không hardcode
trong code), hỗ trợ thêm/sửa/xóa và lọc theo nhóm/tag/loại thiết bị.

Mật khẩu KHÔNG được ghi thẳng vào file inventory. Thay vào đó mỗi thiết
bị chỉ ghi "credentials_env: LAB", chương trình sẽ tự lấy username/password
từ biến môi trường LAB_USERNAME / LAB_PASSWORD (khai báo trong file .env).
"""

import csv
import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from netauto.core.exceptions import InventoryError
from netauto.core.logger import get_logger


class InventoryManager:
    def __init__(self, inventory_path, env_path=".env"):
        self.inventory_path = Path(inventory_path)
        self.logger = get_logger()
        if env_path and Path(env_path).exists():
            load_dotenv(env_path)
        self._devices = []
        self.load()

    # ------------------------------------------------------------------ #
    # Đọc / ghi file inventory
    # ------------------------------------------------------------------ #
    def load(self):
        if not self.inventory_path.exists():
            raise InventoryError(f"Không tìm thấy file inventory: {self.inventory_path}")

        suffix = self.inventory_path.suffix.lower()
        if suffix in (".yml", ".yaml"):
            data = yaml.safe_load(self.inventory_path.read_text(encoding="utf-8")) or {}
            raw_devices = data.get("devices", [])
        elif suffix == ".json":
            data = json.loads(self.inventory_path.read_text(encoding="utf-8"))
            raw_devices = data.get("devices", [])
        elif suffix == ".csv":
            with self.inventory_path.open(newline="", encoding="utf-8") as fh:
                raw_devices = list(csv.DictReader(fh))
        else:
            raise InventoryError(f"Không hỗ trợ định dạng file: {suffix}")

        self._devices = [self._resolve_credentials(d) for d in raw_devices]
        self.logger.info("Đã đọc %d thiết bị từ %s", len(self._devices), self.inventory_path)

    def save(self):
        """Ghi danh sách thiết bị hiện tại xuống file (không ghi mật khẩu)."""
        devices_to_save = []
        for d in self._devices:
            # Không bao giờ ghi mật khẩu xuống file.
            hidden = ["password", "secret"]
            # Nếu tài khoản lấy từ .env thì cũng không ghi username ra file.
            if d.get("credentials_env"):
                hidden.append("username")
            entry = {k: v for k, v in d.items() if k not in hidden}
            devices_to_save.append(entry)
        content = yaml.safe_dump({"devices": devices_to_save}, sort_keys=False, allow_unicode=True)
        self.inventory_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _resolve_credentials(device):
        """Nếu thiết bị có 'credentials_env: LAB' thì lấy username/password
        từ biến môi trường LAB_USERNAME / LAB_PASSWORD / LAB_SECRET."""
        device = dict(device)
        env_key = device.get("credentials_env")
        if env_key:
            device.setdefault("username", os.getenv(f"{env_key}_USERNAME", ""))
            device.setdefault("password", os.getenv(f"{env_key}_PASSWORD", ""))
            device.setdefault("secret", os.getenv(f"{env_key}_SECRET", device.get("password", "")))
        if "port" in device:
            device["port"] = int(device["port"])
        if isinstance(device.get("tags"), str):
            device["tags"] = [t.strip() for t in device["tags"].split(",") if t.strip()]
        return device

    # ------------------------------------------------------------------ #
    # Thêm / sửa / xóa / tìm thiết bị
    # ------------------------------------------------------------------ #
    def all(self):
        return list(self._devices)

    def add(self, device):
        if any(d["name"] == device["name"] for d in self._devices):
            raise InventoryError(f"Thiết bị '{device['name']}' đã tồn tại")
        self._devices.append(self._resolve_credentials(device))

    def remove(self, name):
        before = len(self._devices)
        self._devices = [d for d in self._devices if d["name"] != name]
        if len(self._devices) == before:
            raise InventoryError(f"Không tìm thấy thiết bị '{name}'")

    def update(self, name, **fields):
        for d in self._devices:
            if d["name"] == name:
                d.update(fields)
                return
        raise InventoryError(f"Không tìm thấy thiết bị '{name}'")

    def get(self, name):
        for d in self._devices:
            if d["name"] == name:
                return d
        raise InventoryError(f"Không tìm thấy thiết bị '{name}'")

    def filter(self, group=None, tag=None, device_type=None):
        """Lọc thiết bị theo nhóm, theo nhãn (tag) hoặc theo loại thiết bị."""
        result = self._devices
        if group:
            result = [d for d in result if d.get("group") == group]
        if tag:
            result = [d for d in result if tag in d.get("tags", [])]
        if device_type:
            result = [d for d in result if d.get("device_type") == device_type]
        return result
