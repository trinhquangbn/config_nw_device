"""DeviceFactory - tạo đúng lớp thiết bị theo hãng (mẫu thiết kế Factory).

Khi cần thêm một hãng mới, chỉ cần viết thêm 1 lớp con của NetworkDevice
rồi gọi DeviceFactory.register(...) - không cần sửa lại các lớp đã có.
Nhờ vậy InventoryManager/BatchOperator không cần biết có bao nhiêu hãng,
chỉ cần gọi DeviceFactory.create_device(spec) là ra đúng đối tượng.
"""

from netauto.core.devices.arista_eos import AristaEOSDevice
from netauto.core.devices.cisco_ios import CiscoIOSDevice
from netauto.core.devices.juniper_junos import JuniperJunOSDevice
from netauto.core.devices.vyos import VyOSDevice
from netauto.core.exceptions import InventoryError


class DeviceFactory:
    # "registry" ánh xạ tên hãng (ghi trong inventory) -> lớp Python tương ứng
    _registry = {
        "cisco_ios": CiscoIOSDevice,
        "arista_eos": AristaEOSDevice,
        "juniper_junos": JuniperJunOSDevice,
        "vyos": VyOSDevice,
    }

    @classmethod
    def register(cls, vendor_key, device_cls):
        """Đăng ký thêm một hãng mới mà không cần sửa file này."""
        cls._registry[vendor_key] = device_cls

    @classmethod
    def supported_vendors(cls):
        return list(cls._registry.keys())

    @classmethod
    def create_device(cls, spec):
        """spec là 1 dict lấy từ inventory, ví dụ:
        {"name": "R1", "host": "1.1.1.1", "device_type": "cisco_ios", ...}
        """
        vendor = spec.get("device_type")
        device_cls = cls._registry.get(vendor)
        if device_cls is None:
            raise InventoryError(
                f"Không hỗ trợ device_type '{vendor}'. Các loại hỗ trợ: {cls.supported_vendors()}"
            )
        try:
            return device_cls(
                name=spec["name"],
                host=spec["host"],
                username=spec["username"],
                password=spec["password"],
                port=spec.get("port", 22),
                secret=spec.get("secret"),
                group=spec.get("group", "default"),
                tags=spec.get("tags", []),
            )
        except KeyError as exc:
            raise InventoryError(f"Thiếu trường {exc} cho thiết bị {spec.get('name')}") from exc
