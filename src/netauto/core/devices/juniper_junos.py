"""Thiết bị Juniper JunOS.

JunOS dùng mô hình "candidate config": lệnh cấu hình chỉ được ghi vào bản
nháp, phải gõ "commit" thì mới có hiệu lực. Vì vậy lớp này ghi đè
send_config_set() để thêm bước commit.
"""

from netauto.core.devices.base import NetworkDevice
from netauto.core.exceptions import DeviceConnectionError


class JuniperJunOSDevice(NetworkDevice):
    NETMIKO_DEVICE_TYPE = "juniper_junos"
    CONFIG_ERROR_PATTERN = r"syntax error|unknown command|error:"

    def get_running_config(self):
        return self.send_command("show configuration | display set")

    def get_facts(self):
        version = self.send_command("show version", use_textfsm=True)
        return {
            "vendor": "juniper_junos",
            "hostname": self.name,
            "version": version,
        }

    def send_config_set(self, config_lines, check_errors=True):
        if self._session is None:
            raise DeviceConnectionError(f"{self.name} chưa được kết nối")
        # Phải ở lại chế độ cấu hình để commit. Nếu thoát ra trước khi
        # commit thì JunOS sẽ bỏ các thay đổi chưa được commit.
        output = self._session.send_config_set(config_lines, exit_config_mode=False,
                                               error_pattern=self._error_pattern(check_errors))
        output += self._session.commit()
        output += self._session.exit_config_mode()
        return output

    def save_config(self):
        # Trên JunOS, "commit" đã lưu cấu hình luôn nên không cần làm gì thêm.
        pass
