"""Kiểm thử phần sinh inventory cho Ansible."""

import yaml

from netauto.core.ansible_bridge import AnsibleBridge


def test_sinh_inventory_ansible(tmp_path):
    devices = [
        {"name": "R1", "host": "10.0.0.1", "device_type": "cisco_ios"},
        {"name": "SW2", "host": "10.0.0.2", "device_type": "arista_eos"},
        {"name": "FW1", "host": "10.0.0.3", "device_type": "vyos"},  # chưa hỗ trợ, bị bỏ qua
    ]
    path = AnsibleBridge(tmp_path).generate_inventory(devices)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    groups = data["all"]["children"]
    assert groups["ios_devices"]["hosts"]["R1"]["ansible_host"] == "10.0.0.1"
    assert "SW2" in groups["eos_devices"]["hosts"]
    assert "FW1" not in str(data)
