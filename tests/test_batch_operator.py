"""Kiểm thử BatchOperator bằng cách giả lập (mock) kết nối SSH,
không cần thiết bị thật."""

from unittest.mock import MagicMock, patch

from netauto.core.backup_manager import BackupManager
from netauto.core.batch_operator import BatchOperator
from netauto.core.factory import DeviceFactory


def make_devices(sample_device_spec):
    specs = [
        sample_device_spec,
        dict(sample_device_spec, name="SW1", host="192.0.2.20", device_type="arista_eos"),
    ]
    return [DeviceFactory.create_device(s) for s in specs]


def test_dry_run_khong_ket_noi_thiet_bi(sample_device_spec):
    devices = make_devices(sample_device_spec)
    operator = BatchOperator(max_workers=2)
    with patch("netauto.core.devices.base.ConnectHandler") as fake_connect:
        results = operator.push_batch(devices, ["vlan 10"], dry_run=True)
    fake_connect.assert_not_called()
    assert all(r["dry_run"] and r["success"] for r in results)


def test_mot_thiet_bi_loi_khong_anh_huong_thiet_bi_khac(sample_device_spec, tmp_path):
    devices = make_devices(sample_device_spec)

    session = MagicMock()
    session.send_command.return_value = "hostname SW1"

    def fake_connect(**params):
        if params["host"] == devices[0].host:
            raise RuntimeError("giả lập mất kết nối")
        return session

    with patch("netauto.core.devices.base.ConnectHandler", side_effect=fake_connect):
        operator = BatchOperator(max_workers=2, backup_manager=BackupManager(tmp_path))
        results = operator.push_batch(devices, ["vlan 10"], dry_run=False, auto_rollback=False)

    assert results[0]["success"] is False
    assert results[1]["success"] is True
    # Lệnh cấu hình được gửi kèm mẫu lỗi để Netmiko phát hiện lệnh sai.
    session.send_config_set.assert_called_once_with(
        ["vlan 10"], error_pattern=r"% Invalid|% Incomplete|% Ambiguous")


def test_tu_dong_rollback_khi_ap_cau_hinh_loi(sample_device_spec, tmp_path):
    device = DeviceFactory.create_device(sample_device_spec)

    session = MagicMock()
    session.send_command.return_value = "Building configuration...\nhostname R1\nend"
    # Lần gửi cấu hình đầu tiên lỗi, lần thứ hai (rollback) thành công.
    session.send_config_set.side_effect = [RuntimeError("lệnh sai"), "ok"]

    with patch("netauto.core.devices.base.ConnectHandler", return_value=session):
        operator = BatchOperator(max_workers=1, backup_manager=BackupManager(tmp_path))
        result = operator.push_batch([device], ["lenh sai"], dry_run=False)[0]

    assert result["success"] is False
    assert result["rolled_back"] is True
    # Khi rollback chỉ gửi lại dòng cấu hình thật, bỏ dòng tiêu đề và "end".
    rollback_call = session.send_config_set.call_args_list[1]
    assert rollback_call.args[0] == ["hostname R1"]
    # Khi rollback không dừng lại vì lỗi (không truyền mẫu lỗi).
    assert rollback_call.kwargs["error_pattern"] == ""


def test_juniper_co_commit(sample_device_spec):
    device = DeviceFactory.create_device(dict(sample_device_spec, device_type="juniper_junos"))
    session = MagicMock()
    session.send_config_set.return_value = ""
    session.commit.return_value = ""
    session.exit_config_mode.return_value = ""

    with patch("netauto.core.devices.base.ConnectHandler", return_value=session):
        result = device.execute_task(device.push_config, ["set system host-name J1"])

    assert result["success"] is True
    session.commit.assert_called_once()
