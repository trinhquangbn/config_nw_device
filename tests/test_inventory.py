import textwrap

from netauto.core.inventory import InventoryManager


def test_load_and_filter(tmp_path, monkeypatch):
    inv_file = tmp_path / "inventory.yaml"
    inv_file.write_text(textwrap.dedent("""
        devices:
          - name: R1
            host: 10.0.0.1
            device_type: cisco_ios
            group: core
            tags: [core, ospf]
            username: admin
            password: pass
          - name: SW1
            host: 10.0.0.2
            device_type: arista_eos
            group: access
            tags: [access]
            username: admin
            password: pass
    """))
    inv = InventoryManager(str(inv_file), env_path=None)
    assert len(inv.all()) == 2
    assert [d["name"] for d in inv.filter(group="core")] == ["R1"]
    assert [d["name"] for d in inv.filter(tag="access")] == ["SW1"]


def test_add_remove(tmp_path):
    inv_file = tmp_path / "inventory.yaml"
    inv_file.write_text("devices: []\n")
    inv = InventoryManager(str(inv_file), env_path=None)
    inv.add({"name": "NEW1", "host": "1.1.1.1", "device_type": "vyos", "username": "a", "password": "b"})
    assert inv.get("NEW1")["host"] == "1.1.1.1"
    inv.remove("NEW1")
    assert inv.all() == []


def test_save_khong_ghi_mat_khau(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_USERNAME", "admin")
    monkeypatch.setenv("LAB_PASSWORD", "matkhau123")
    inv_file = tmp_path / "inventory.yaml"
    inv_file.write_text("devices: []\n")
    inv = InventoryManager(str(inv_file), env_path=None)
    inv.add({"name": "R1", "host": "1.1.1.1", "device_type": "cisco_ios", "credentials_env": "LAB"})
    assert inv.get("R1")["password"] == "matkhau123"  # đọc được từ biến môi trường

    inv.save()
    content = inv_file.read_text()
    assert "matkhau123" not in content
    assert "admin" not in content
    assert "credentials_env: LAB" in content
