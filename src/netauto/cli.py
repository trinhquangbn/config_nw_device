"""Giao diện dòng lệnh (CLI) của chương trình.

File này chỉ đọc tham số dòng lệnh rồi gọi các lớp trong netauto.core.
Toàn bộ xử lý nằm trong core, nên giao diện web (web/app.py) dùng lại
đúng các lớp đó và cho cùng một kết quả.

Cách chạy (từ thư mục gốc của dự án):
    python main.py inventory-list
    python main.py backup --group access
"""

import argparse
import json
import time
from pathlib import Path

from netauto.core import settings
from netauto.core.ansible_bridge import AnsibleBridge
from netauto.core.backup_manager import BackupManager
from netauto.core.batch_operator import BatchOperator
from netauto.core.factory import DeviceFactory
from netauto.core.inventory import InventoryManager
from netauto.core.report import ReportGenerator
from netauto.core.template_engine import TemplateEngine


# ---------------------------------------------------------------------- #
# Hàm hỗ trợ
# ---------------------------------------------------------------------- #
def build_devices(inventory, args):
    """Lọc thiết bị theo tham số --group/--tag/--device-type rồi tạo đối
    tượng thiết bị tương ứng bằng DeviceFactory."""
    specs = inventory.filter(group=args.group, tag=args.tag, device_type=args.device_type)
    return [DeviceFactory.create_device(spec) for spec in specs]


def make_operator():
    return BatchOperator(max_workers=settings.MAX_WORKERS,
                         backup_manager=BackupManager(settings.BACKUP_DIR))


def show_results(results, output_format, prefix):
    """In kết quả ra màn hình và ghi báo cáo JSON + HTML."""
    if output_format == "json":
        print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
    else:
        for r in results:
            status = "OK" if r.get("success") else "FAILED"
            # Gộp thông báo lỗi thành 1 dòng và cắt bớt cho gọn, chi tiết xem trong báo cáo.
            error = " ".join(r.get("error", "").split())[:150]
            print(f"{r['device']:<15} {status:<7} {error}")

    report = ReportGenerator(settings.REPORT_DIR)
    report.to_json(results, prefix=prefix)
    html_path = report.to_html(results, prefix=prefix)
    print(f"\nBáo cáo đã được ghi tại: {html_path}")


# ---------------------------------------------------------------------- #
# Các lệnh
# ---------------------------------------------------------------------- #
def cmd_inventory_list(args, inventory):
    for d in inventory.filter(group=args.group, tag=args.tag, device_type=args.device_type):
        tags = ",".join(d.get("tags", []))
        print(f"{d['name']:<15} {d['host']:<16} {d['device_type']:<14} "
              f"group={d.get('group', '-'):<10} tags={tags}")


def cmd_inventory_add(args, inventory):
    inventory.add({
        "name": args.name,
        "host": args.host,
        "device_type": args.device_type,
        "port": args.port,
        "group": args.group,
        "tags": args.tags.split(",") if args.tags else [],
        "credentials_env": args.credentials_env,
    })
    inventory.save()
    print(f"Đã thêm thiết bị '{args.name}'.")


def cmd_inventory_remove(args, inventory):
    inventory.remove(args.name)
    inventory.save()
    print(f"Đã xóa thiết bị '{args.name}'.")


def cmd_check(args, inventory):
    devices = build_devices(inventory, args)
    results = make_operator().check_all(devices)
    show_results(results, args.output, prefix="check")


def cmd_collect(args, inventory):
    devices = build_devices(inventory, args)
    results = make_operator().collect_facts(devices)
    show_results(results, args.output, prefix="facts")


def cmd_backup(args, inventory):
    devices = build_devices(inventory, args)
    operator = make_operator()

    if not args.every:
        show_results(operator.backup_all(devices), args.output, prefix="backup")
        return

    # Sao lưu theo lịch: cứ args.every phút chạy lại một lần.
    print(f"Sao lưu tự động mỗi {args.every} phút. Bấm Ctrl+C để dừng.")
    try:
        while True:
            show_results(operator.backup_all(devices), args.output, prefix="backup")
            time.sleep(args.every * 60)
    except KeyboardInterrupt:
        print("Đã dừng sao lưu tự động.")


def cmd_diff(args, inventory):
    print(BackupManager(settings.BACKUP_DIR).diff(args.device))


def cmd_restore(args, inventory):
    device = DeviceFactory.create_device(inventory.get(args.device))
    manager = BackupManager(settings.BACKUP_DIR)
    if args.file:
        backup_file = Path(args.file)
    else:
        backups = manager.list_backups(args.device)
        if not backups:
            print(f"Chưa có bản sao lưu nào của {args.device}.")
            return
        backup_file = backups[-1]
    result = manager.restore(device, backup_file)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


def find_vars_file(name):
    """Tìm file biến: thử đúng đường dẫn người dùng gõ trước, không có thì
    tìm trong thư mục variables/. Trả về None nếu không thấy."""
    for path in (Path(name), Path(settings.VARS_DIR) / name):
        if path.exists():
            return path
    return None


def cmd_push(args, inventory):
    devices = build_devices(inventory, args)
    variables = {}
    if args.vars:
        vars_file = find_vars_file(args.vars)
        if vars_file is None:
            print(f"Không tìm thấy file biến '{args.vars}' (đã tìm ở thư mục hiện tại "
                  f"và thư mục {settings.VARS_DIR}/).")
            return
        variables = json.loads(vars_file.read_text(encoding="utf-8"))
    config_lines = TemplateEngine(settings.TEMPLATES_DIR).render(args.template, variables)

    print("Cấu hình sẽ được áp dụng:")
    print("\n".join(config_lines))
    print("-" * 40)

    results = make_operator().push_batch(devices, config_lines, dry_run=args.dry_run,
                                         auto_rollback=not args.no_rollback)
    show_results(results, args.output, prefix="push")


def cmd_ansible_inventory(args, inventory):
    path = AnsibleBridge().generate_inventory(inventory.all())
    print(f"Đã sinh inventory cho Ansible: {path}")


def cmd_ansible_run(args, inventory):
    if not AnsibleBridge.is_installed():
        print("Không tìm thấy lệnh ansible-playbook. Ansible không chạy trực tiếp trên "
              "Windows, hãy cài WSL (Ubuntu) rồi chạy lệnh này trong WSL.")
        return
    code = AnsibleBridge().run_playbook(args.playbook, check=args.check)
    print("Chạy playbook thành công." if code == 0 else f"Playbook lỗi (mã {code}).")


# ---------------------------------------------------------------------- #
# Khai báo tham số dòng lệnh
# ---------------------------------------------------------------------- #
def add_filter_options(parser):
    """Các tham số lọc thiết bị, dùng chung cho nhiều lệnh."""
    parser.add_argument("--group", help="Lọc theo nhóm")
    parser.add_argument("--tag", help="Lọc theo nhãn")
    parser.add_argument("--device-type", dest="device_type", help="Lọc theo loại thiết bị")


def add_output_option(parser):
    parser.add_argument("--output", choices=["table", "json"], default="table")


def build_parser():
    parser = argparse.ArgumentParser(prog="netauto",
                                     description="Công cụ cấu hình mạng hàng loạt đa nhà cung cấp")
    parser.add_argument("--inventory", default=settings.INVENTORY_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inventory-list", help="Liệt kê thiết bị")
    add_filter_options(p)
    p.set_defaults(func=cmd_inventory_list)

    p = sub.add_parser("inventory-add", help="Thêm thiết bị")
    p.add_argument("--name", required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--device-type", dest="device_type", required=True)
    p.add_argument("--port", type=int, default=22)
    p.add_argument("--group", default="default")
    p.add_argument("--tags", default="")
    p.add_argument("--credentials-env", dest="credentials_env", required=True)
    p.set_defaults(func=cmd_inventory_add)

    p = sub.add_parser("inventory-remove", help="Xóa thiết bị")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_inventory_remove)

    p = sub.add_parser("check", help="Kiểm tra kết nối tới thiết bị")
    add_filter_options(p)
    add_output_option(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("collect", help="Thu thập thông tin thiết bị")
    add_filter_options(p)
    add_output_option(p)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("backup", help="Sao lưu cấu hình")
    add_filter_options(p)
    add_output_option(p)
    p.add_argument("--every", type=int, default=0, help="Tự sao lưu mỗi N phút")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("diff", help="So sánh 2 bản sao lưu gần nhất")
    p.add_argument("--device", required=True)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("restore", help="Khôi phục cấu hình từ bản sao lưu")
    p.add_argument("--device", required=True)
    p.add_argument("--file", help="File sao lưu (mặc định là bản mới nhất)")
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("push", help="Áp cấu hình hàng loạt từ template")
    add_filter_options(p)
    add_output_option(p)
    p.add_argument("--template", required=True)
    p.add_argument("--vars", help="File JSON chứa biến cho template")
    p.add_argument("--dry-run", action="store_true", help="Chỉ xem trước, không áp dụng")
    p.add_argument("--no-rollback", action="store_true", help="Không tự rollback khi lỗi")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("ansible-inventory", help="Sinh inventory cho Ansible từ inventory.yaml")
    p.set_defaults(func=cmd_ansible_inventory)

    p = sub.add_parser("ansible-run", help="Chạy một Ansible playbook")
    p.add_argument("--playbook", required=True, help="Ví dụ: backup_config.yml")
    p.add_argument("--check", action="store_true", help="Chạy thử, không áp dụng")
    p.set_defaults(func=cmd_ansible_run)

    return parser


def main():
    args = build_parser().parse_args()
    inventory = InventoryManager(args.inventory)
    args.func(args, inventory)


if __name__ == "__main__":
    main()
