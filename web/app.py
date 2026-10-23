"""Giao diện web đơn giản bằng Flask (điểm cộng mục 5.1).

File này CHỈ gọi lại các lớp/hàm trong netauto.core, không viết thêm logic
xử lý thiết bị ở đây - đúng yêu cầu "giao diện phải tách biệt khỏi phần
lõi nghiệp vụ". Phần lõi (src/netauto/cli.py) vẫn chạy độc lập qua CLI.
"""

import json
import os
import sys
from pathlib import Path

# Thêm thư mục src vào đường dẫn tìm module để import được gói netauto.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from dotenv import load_dotenv  # noqa: E402
from flask import Flask, flash, redirect, render_template, request, url_for  # noqa: E402

from netauto.core import settings  # noqa: E402
from netauto.core.backup_manager import BackupManager  # noqa: E402
from netauto.core.batch_operator import BatchOperator  # noqa: E402
from netauto.core.factory import DeviceFactory  # noqa: E402
from netauto.core.inventory import InventoryManager  # noqa: E402
from netauto.core.exceptions import TemplateRenderError  # noqa: E402
from netauto.core.template_engine import TemplateEngine  # noqa: E402

load_dotenv(BASE_DIR / ".env")
app = Flask(__name__)
# Khóa bí mật của Flask lấy từ biến môi trường, không viết cứng trong code.
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chi-dung-khi-thu-nghiem")

# Gợi ý file biến (trong thư mục variables/) đi kèm với từng template.
# Khi thêm template mới thì thêm 1 dòng vào đây.
SUGGESTED_VARS = {
    "vlan.j2": "sample_vars.json",
    "ospf.j2": "ospf_vars.json",
    "acl.j2": "acl_vars.json",
    "interface.j2": "interface_vars.json",
    "internet.j2": "internet_vars.json",
    "switch_ports.j2": "switch_ports_vars.json",
    "dhcp.j2": "phong_ban_vars.json",
    "router_on_a_stick.j2": "phong_ban_vars.json",
    "svi.j2": "phong_ban_vars.json",
}


def get_inventory():
    return InventoryManager(str(BASE_DIR / settings.INVENTORY_PATH), env_path=str(BASE_DIR / ".env"))


def get_operator():
    return BatchOperator(max_workers=settings.MAX_WORKERS,
                         backup_manager=BackupManager(str(BASE_DIR / settings.BACKUP_DIR)))


def load_var_files():
    """Đọc các file JSON trong thư mục variables/, trả về {tên file: nội dung}."""
    vars_dir = BASE_DIR / settings.VARS_DIR
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(vars_dir.glob("*.json"))}


@app.route("/")
def dashboard():
    inventory = get_inventory()
    devices = inventory.all()
    bm = BackupManager(str(BASE_DIR / settings.BACKUP_DIR))
    backup_counts = {d["name"]: len(bm.list_backups(d["name"])) for d in devices}
    stats = {
        "total_devices": len(devices),
        "groups": sorted({d.get("group", "-") for d in devices}),
        "total_backups": sum(backup_counts.values()),
    }
    return render_template("dashboard.html", devices=devices, stats=stats, backup_counts=backup_counts)


@app.route("/devices")
def devices_view():
    inventory = get_inventory()
    group = request.args.get("group") or None
    tag = request.args.get("tag") or None
    devices = inventory.filter(group=group, tag=tag)
    return render_template("devices.html", devices=devices, group=group, tag=tag)


@app.route("/collect", methods=["POST"])
def collect():
    inventory = get_inventory()
    names = request.form.getlist("names")
    specs = [d for d in inventory.all() if not names or d["name"] in names]
    devices = [DeviceFactory.create_device(s) for s in specs]
    results = get_operator().collect_facts(devices)
    flash(f"Đã thu thập thông tin từ {len(results)} thiết bị.")
    return render_template("results.html", results=results, action="Thu thập thông tin")


@app.route("/backup", methods=["POST"])
def backup():
    inventory = get_inventory()
    names = request.form.getlist("names")
    specs = [d for d in inventory.all() if not names or d["name"] in names]
    devices = [DeviceFactory.create_device(s) for s in specs]
    results = get_operator().backup_all(devices)
    flash(f"Đã sao lưu {len(results)} thiết bị.")
    return render_template("results.html", results=results, action="Sao lưu cấu hình")


@app.route("/push", methods=["GET", "POST"])
def push():
    engine = TemplateEngine(str(BASE_DIR / settings.TEMPLATES_DIR))
    inventory = get_inventory()
    if request.method == "GET":
        templates = engine.list_templates()
        hints = {t: engine.get_description(t) for t in templates}
        return render_template("push.html", devices=inventory.all(), templates=templates,
                               hints=hints, var_files=load_var_files(), suggested=SUGGESTED_VARS)

    names = request.form.getlist("names")
    template_name = request.form["template"]
    dry_run = request.form.get("dry_run") == "on"
    try:
        context = json.loads(request.form.get("vars_json") or "{}")
    except json.JSONDecodeError as exc:
        flash(f"Biến JSON không hợp lệ: {exc}")
        return redirect(url_for("push"))

    specs = [d for d in inventory.all() if d["name"] in names]
    devices = [DeviceFactory.create_device(s) for s in specs]
    try:
        config_lines = engine.render(template_name, context)
    except TemplateRenderError as exc:
        # Ví dụ chọn nhầm file biến nên template thiếu biến.
        flash(str(exc))
        return redirect(url_for("push"))
    results = get_operator().push_batch(devices, config_lines, dry_run=dry_run)
    action_label = "Áp cấu hình (dry-run)" if dry_run else "Áp cấu hình (đã thực thi)"
    return render_template("results.html", results=results, action=action_label,
                           rendered_config=config_lines)


@app.route("/reports")
def reports():
    report_dir = BASE_DIR / settings.REPORT_DIR
    files = sorted(report_dir.glob("*.html"), reverse=True)
    return render_template("reports.html", files=files)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
