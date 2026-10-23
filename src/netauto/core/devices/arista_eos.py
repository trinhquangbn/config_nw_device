"""Thiết bị Arista EOS."""

from netauto.core.devices.base import NetworkDevice


class AristaEOSDevice(NetworkDevice):
    NETMIKO_DEVICE_TYPE = "arista_eos"
    NEEDS_ENABLE = True  # Arista cũng cần vào chế độ enable như Cisco

    def get_running_config(self):
        return self.send_command("show running-config")

    def get_facts(self):
        version = self.send_command("show version", use_textfsm=True)
        interfaces = self.send_command("show ip interface brief", use_textfsm=True)
        return {
            "vendor": "arista_eos",
            "hostname": self.name,
            "version": version,
            "interfaces": interfaces,
        }

    def save_config(self):
        # Arista cũng lưu bằng "write memory" giống Cisco.
        self._session.save_config()
