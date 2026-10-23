"""Kết nối chương trình Python với Ansible (điểm cộng mục 5.2).

Hai việc:
1. Sinh file inventory cho Ansible (ansible/inventory/hosts.yml) từ chính
   file config/inventory.yaml của chương trình, để chỉ phải khai báo thiết
   bị ở một nơi.
2. Gọi lệnh ansible-playbook từ Python bằng module subprocess.
"""

import shutil
import subprocess
from pathlib import Path

import yaml

# Ánh xạ device_type của chương trình sang nhóm và network_os của Ansible.
# Hiện mới viết playbook cho Cisco IOS và Arista EOS.
ANSIBLE_GROUPS = {
    "cisco_ios": ("ios_devices", "cisco.ios.ios"),
    "arista_eos": ("eos_devices", "arista.eos.eos"),
}


class AnsibleBridge:
    def __init__(self, ansible_dir="ansible"):
        self.ansible_dir = Path(ansible_dir)
        self.inventory_file = self.ansible_dir / "inventory" / "hosts.yml"

    def generate_inventory(self, devices):
        """Sinh file hosts.yml từ danh sách thiết bị (list dict) của
        InventoryManager. Không ghi mật khẩu vào file này, mật khẩu nằm
        trong vault.yml đã mã hóa."""
        children = {}
        for device in devices:
            if device["device_type"] not in ANSIBLE_GROUPS:
                continue  # hãng chưa có playbook thì bỏ qua
            group, network_os = ANSIBLE_GROUPS[device["device_type"]]
            if group not in children:
                children[group] = {
                    "vars": {
                        "ansible_network_os": network_os,
                        "ansible_connection": "ansible.netcommon.network_cli",
                    },
                    "hosts": {},
                }
            children[group]["hosts"][device["name"]] = {"ansible_host": device["host"]}

        self.inventory_file.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.safe_dump({"all": {"children": children}}, sort_keys=False)
        self.inventory_file.write_text(content, encoding="utf-8")
        return self.inventory_file

    @staticmethod
    def is_installed():
        """Kiểm tra máy đã có lệnh ansible-playbook chưa.
        Ansible không chạy trực tiếp trên Windows, phải dùng Linux hoặc WSL."""
        return shutil.which("ansible-playbook") is not None

    def run_playbook(self, playbook_name, check=False):
        """Chạy một playbook trong thư mục ansible/playbooks.
        check=True tương đương dry-run (chỉ xem thay đổi, không áp dụng)."""
        command = [
            "ansible-playbook",
            "-i", "inventory/hosts.yml",
            f"playbooks/{playbook_name}",
            "--ask-vault-pass",
        ]
        if check:
            command += ["--check", "--diff"]
        # cwd=ansible_dir để các đường dẫn tương đối trong playbook đúng.
        completed = subprocess.run(command, cwd=self.ansible_dir)
        return completed.returncode
