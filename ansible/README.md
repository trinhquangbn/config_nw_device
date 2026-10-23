# Phần Ansible (điểm cộng mục 5.2)

## Cấu trúc thư mục

```
ansible/
├── inventory/
│   ├── hosts.yml                 # danh sách thiết bị (có thể tự sinh từ Python)
│   └── group_vars/all/
│       ├── vars.yml              # biến dùng chung
│       └── vault.yml             # tài khoản đăng nhập, PHẢI mã hóa bằng Ansible Vault
├── playbooks/
│   ├── backup_config.yml         # sao lưu cấu hình
│   └── push_config.yml           # cấu hình VLAN hàng loạt từ template
└── templates/
    └── vlan.j2                   # template Jinja2
```

## Chạy thử

```bash
cd ansible
ansible-galaxy collection install cisco.ios arista.eos ansible.netcommon
ansible-vault encrypt inventory/group_vars/all/vault.yml

ansible-playbook -i inventory/hosts.yml playbooks/backup_config.yml --ask-vault-pass
ansible-playbook -i inventory/hosts.yml playbooks/push_config.yml --ask-vault-pass --check --diff   # chạy thử
ansible-playbook -i inventory/hosts.yml playbooks/push_config.yml --ask-vault-pass                  # áp dụng thật
```

## Kết hợp với chương trình Python

File `src/netauto/core/ansible_bridge.py` làm 2 việc:

- Sinh `inventory/hosts.yml` từ `config/inventory.yaml` của chương trình, để chỉ khai báo thiết bị ở một nơi:
  `python main.py ansible-inventory`
- Gọi `ansible-playbook` từ Python bằng `subprocess`:
  `python main.py ansible-run --playbook backup_config.yml` (thêm `--check` để chạy thử)

## So sánh hai cách làm

| Tiêu chí | Python (Netmiko, hướng đối tượng) | Ansible Playbook |
| --- | --- | --- |
| Cách viết | Tự viết từng bước: kết nối, gửi lệnh, sao lưu, rollback | Khai báo trạng thái mong muốn, Ansible tự tính phần cần thay đổi |
| Hỗ trợ nhiều hãng | Lớp con theo hãng + Factory, không cần if/else | Mỗi hãng một module riêng (`ios_config`, `eos_config`) kèm điều kiện `when` |
| Mức độ linh hoạt | Cao: tự quyết định cách xử lý lỗi, chạy song song, rollback | Phụ thuộc vào module có sẵn, nhưng có sẵn chế độ chạy thử `--check` |
| Thời gian viết | Lâu hơn vì phải tự viết nhiều | Nhanh hơn với các tác vụ phổ biến |
| Bảo mật mật khẩu | File `.env` (không đưa lên Git) | Ansible Vault mã hóa file biến |
