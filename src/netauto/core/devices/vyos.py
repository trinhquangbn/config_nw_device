"""Thiết bị VyOS.

Giống JunOS, VyOS cần "commit" để cấu hình có hiệu lực và "save" để cấu
hình còn lại sau khi khởi động lại thiết bị.
"""

from netauto.core.devices.base import NetworkDevice
from netauto.core.exceptions import DeviceConnectionError


class VyOSDevice(NetworkDevice):
    NETMIKO_DEVICE_TYPE = "vyos"
    CONFIG_ERROR_PATTERN = r"Invalid command|is not valid|Set failed"

    def get_running_config(self):
        return self.send_command("show configuration commands")

    def get_facts(self):
        version = self.send_command("show version")
        return {
            "vendor": "vyos",
            "hostname": self.name,
            "version": version,
        }

    def send_config_set(self, config_lines, check_errors=True):
        if self._session is None:
            raise DeviceConnectionError(f"{self.name} chưa được kết nối")
        output = self._session.send_config_set(config_lines, exit_config_mode=False,
                                               error_pattern=self._error_pattern(check_errors))
        output += self._session.commit()
        return output

    def save_config(self):
        # Netmiko gửi lệnh "save" trong chế độ cấu hình của VyOS.
        self._session.save_config()
