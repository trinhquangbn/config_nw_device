from pathlib import Path

from netauto.core.template_engine import TemplateEngine

ROOT = Path(__file__).resolve().parent.parent


def test_render_vlan_template_produces_expected_lines():
    engine = TemplateEngine(str(ROOT / "templates_config"))
    lines = engine.render("vlan.j2", {"vlans": [{"id": 10, "name": "USERS"}]})
    assert "vlan 10" in lines
    assert " name USERS" in lines
    # Comment lines starting with '!' must be stripped.
    assert not any(line.strip().startswith("!") for line in lines)


def test_ospf_khong_bat_buoc_router_id():
    engine = TemplateEngine(str(ROOT / "templates_config"))
    lines = engine.render("ospf.j2", {
        "process_id": 1,
        "networks": [{"network": "10.0.12.0", "wildcard": "0.0.0.3", "area": 0}],
    })
    assert lines == ["router ospf 1", " network 10.0.12.0 0.0.0.3 area 0"]


def test_lay_chu_thich_dau_template(tmp_path):
    (tmp_path / "demo.j2").write_text(
        "! Cấu hình demo\n! Biến: vlans\n!\n! Chú thích phía dưới, không lấy\nvlan 10\n",
        encoding="utf-8")
    engine = TemplateEngine(str(tmp_path))
    assert engine.get_description("demo.j2") == "Cấu hình demo\nBiến: vlans"
