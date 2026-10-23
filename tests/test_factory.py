"""Kiểm thử Factory và các tính chất OOP của lớp thiết bị."""

import pytest

from netauto.core.devices.base import NetworkDevice
from netauto.core.devices.cisco_ios import CiscoIOSDevice
from netauto.core.exceptions import InventoryError
from netauto.core.factory import DeviceFactory


def test_factory_tao_dung_lop(sample_device_spec):
    device = DeviceFactory.create_device(sample_device_spec)
    assert isinstance(device, CiscoIOSDevice)
    assert device.name == "R1-TEST"


def test_factory_bao_loi_khi_sai_hang(sample_device_spec):
    spec = dict(sample_device_spec, device_type="hang_khong_co")
    with pytest.raises(InventoryError):
        DeviceFactory.create_device(spec)


def test_factory_bao_loi_khi_thieu_truong(sample_device_spec):
    spec = dict(sample_device_spec)
    del spec["host"]
    with pytest.raises(InventoryError):
        DeviceFactory.create_device(spec)


def test_khong_tao_duoc_doi_tuong_tu_lop_truu_tuong():
    # Lớp trừu tượng không khởi tạo trực tiếp được (TypeError).
    with pytest.raises(TypeError):
        NetworkDevice("X", "1.1.1.1", "admin", "pass")


def test_dong_goi_mat_khau(sample_device_spec):
    device = DeviceFactory.create_device(sample_device_spec)
    # Getter không trả về mật khẩu thật.
    assert device.password == "********"
    # Không truy cập trực tiếp được thuộc tính __password từ bên ngoài.
    with pytest.raises(AttributeError):
        print(device.__password)
    # repr không chứa mật khẩu.
    assert "secret" not in repr(device)
    # Setter kiểm tra giá trị rỗng.
    with pytest.raises(ValueError):
        device.password = ""


def test_da_hinh_nhieu_hang(sample_device_spec):
    specs = [
        sample_device_spec,
        dict(sample_device_spec, name="SW1", device_type="arista_eos"),
        dict(sample_device_spec, name="FW1", device_type="vyos"),
        dict(sample_device_spec, name="J1", device_type="juniper_junos"),
    ]
    devices = [DeviceFactory.create_device(s) for s in specs]
    types = [d.NETMIKO_DEVICE_TYPE for d in devices]
    assert types == ["cisco_ios", "arista_eos", "vyos", "juniper_junos"]
    # Chỉ Cisco và Arista cần vào chế độ enable.
    assert [d.NEEDS_ENABLE for d in devices] == [True, True, False, False]
