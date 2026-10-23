"""Thiết bị Cisco IOS / IOS-XE."""

from netauto.core.devices.base import NetworkDevice


class CiscoIOSDevice(NetworkDevice):
    NETMIKO_DEVICE_TYPE = "cisco_ios"
    NEEDS_ENABLE = True  # Cisco cần vào chế độ enable mới cấu hình được

    def get_running_config(self):
        return self.send_command("show running-config")

    def get_facts(self):
        # use_textfsm=True: nhận về danh sách dict thay vì chuỗi văn bản.
        version = self.send_command("show version", use_textfsm=True)
        interfaces = self.send_command("show ip interface brief", use_textfsm=True)
        return {
            "vendor": "cisco_ios",
            "hostname": self.name,
            "version": version,
            "interfaces": interfaces,
        }

    def save_config(self):
        # Trên Cisco, Netmiko gửi lệnh "write memory".
        self._session.save_config()
