# NetAuto - Công cụ cấu hình mạng hàng loạt đa nhà cung cấp

Bài tập lớn môn Lập trình hướng đối tượng. Đề tài: **Công cụ cấu hình hàng
loạt đa nhà cung cấp** (template Jinja2, chạy thử dry-run, áp cấu hình song
song, tự rollback khi lỗi).

Thư viện tự động hóa mạng chính: **Netmiko**.

## 1. Vì sao chọn Netmiko?

| Thư viện | Ưu điểm | Nhược điểm |
| --- | --- | --- |
| **Netmiko** (nhóm chọn) | Hỗ trợ sẵn nhiều hãng qua SSH, cách dùng đơn giản, dễ học | Chỉ làm việc qua CLI, không có NETCONF/REST |
| Paramiko | Linh hoạt, là nền tảng của Netmiko | Phải tự xử lý prompt, chờ kết quả, tốn nhiều công |
| NAPALM | Dữ liệu trả về đã được chuẩn hóa | Ít hãng hơn, không mạnh khi gửi lệnh CLI tùy ý |
| Nornir | Chạy song song và quản lý inventory tốt | Phải học thêm framework, vẫn cần Netmiko để kết nối |

## 2. Cấu trúc thư mục

```
network_automation_toolkit/
├── main.py                    # Điểm khởi chạy chương trình (CLI)
├── src/netauto/
│   ├── cli.py                 # Xử lý tham số dòng lệnh
│   └── core/
│       ├── devices/
│       │   ├── base.py        # Lớp trừu tượng NetworkDevice
│       │   ├── cisco_ios.py   # Các lớp con theo hãng
│       │   ├── arista_eos.py
│       │   ├── juniper_junos.py
│       │   └── vyos.py
│       ├── factory.py         # DeviceFactory (mẫu Factory)
│       ├── inventory.py       # Quản lý danh sách thiết bị
│       ├── template_engine.py # Tạo cấu hình từ template Jinja2
│       ├── backup_manager.py  # Sao lưu, so sánh, khôi phục
│       ├── batch_operator.py  # Chạy song song, dry-run, rollback
│       ├── ansible_bridge.py  # Sinh inventory và chạy playbook Ansible
│       ├── report.py          # Tạo báo cáo JSON/HTML
│       ├── logger.py          # Ghi log
│       ├── settings.py        # Các đường dẫn mặc định
│       └── exceptions.py      # Các lớp lỗi riêng
├── templates_config/          # Template Jinja2 (vlan, interface, ospf, acl)
├── config/inventory.yaml.example
├── web/                       # Giao diện web Flask (điểm cộng)
├── ansible/                   # Ansible Playbook (điểm cộng)
├── tests/                     # Kiểm thử tự động (pytest)
├── data/backups/, data/reports/, logs/
├── .env.example
└── requirements.txt
```

## 3. Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config/inventory.yaml.example config/inventory.yaml   # sửa IP cho đúng topology
cp .env.example .env                                      # điền tài khoản SSH của lab
```

## 4. Sử dụng (chạy từ thư mục gốc của dự án)

```bash
# Quản lý danh sách thiết bị
python main.py inventory-list --group access
python main.py inventory-add --name SW3 --host 192.168.100.15 \
    --device-type cisco_ios --group access --tags access --credentials-env LAB
python main.py inventory-remove --name SW3

# Kiểm tra kết nối và thu thập thông tin
python main.py check
python main.py collect --group access --output json

# Sao lưu (một lần, hoặc tự động mỗi 60 phút)
python main.py backup
python main.py backup --every 60

# So sánh 2 bản sao lưu gần nhất và khôi phục
python main.py diff --device SW1-ACCESS
python main.py restore --device SW1-ACCESS

# Cấu hình hàng loạt: xem trước (dry-run) rồi áp dụng thật
python main.py push --group access --template vlan.j2 --vars sample_vars.json --dry-run
python main.py push --group access --template vlan.j2 --vars sample_vars.json

# Ansible (điểm cộng)
python main.py ansible-inventory
python main.py ansible-run --playbook backup_config.yml --check
```

Mỗi lệnh đều ghi log vào `logs/netauto.log` và tạo báo cáo trong `data/reports/`.

## 5. Giao diện web (điểm cộng) 

```bash
Tạo Secret: python -c "import secrets; print(secrets.token_hex(32))"
python web/app.py
# Mở trình duyệt: http://localhost:5000
```

## 6. Ansible Playbook

Xem `ansible/README.md`.

## 7. Chạy kiểm thử và kiểm tra PEP 8

```bash
pytest tests -v

pip install flake8 && flake8
```

Các test dùng `unittest.mock` để giả lập kết nối SSH nên không cần thiết bị
thật. Test kiểm tra: Factory tạo đúng lớp, không khởi tạo được lớp trừu
tượng, mật khẩu được đóng gói, dry-run không kết nối thiết bị, một thiết bị
lỗi không ảnh hưởng thiết bị khác, tự rollback khi lỗi, Juniper có commit,
inventory không ghi mật khẩu ra file, sinh inventory cho Ansible.

## 8. Bốn tính chất OOP nằm ở đâu

- **Trừu tượng**: `NetworkDevice` trong `core/devices/base.py` kế thừa `ABC`,
  có 3 phương thức `@abstractmethod` mà lớp con bắt buộc phải viết.
- **Kế thừa**: `CiscoIOSDevice`, `AristaEOSDevice`, `JuniperJunOSDevice`,
  `VyOSDevice` kế thừa `NetworkDevice`.
- **Đa hình**: `BatchOperator` gọi `device.get_facts()`, `device.push_config()`
  cho danh sách thiết bị nhiều hãng mà không có if/else theo hãng. Juniper và
  VyOS ghi đè `send_config_set()` để thêm bước commit.
- **Đóng gói**: mật khẩu lưu trong `__password`, chỉ đổi được qua property
  setter (có kiểm tra giá trị rỗng), getter luôn trả về `********`. Mật khẩu
  thật nằm trong file `.env`, không đưa lên Git.
- **Mẫu thiết kế**: Factory (`DeviceFactory`). Ngoài ra `NetworkDevice` dùng
  context manager (`with device:`) để tự kết nối và ngắt kết nối.
  
## 9. Video Demo

https://drive.google.com/file/d/1yRhdDCLwyN3728Xxr3GhXAnobBdKDwmG/view?usp=sharing
