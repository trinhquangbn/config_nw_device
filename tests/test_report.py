"""Kiểm thử ghi báo cáo có tiếng Việt (trên Windows dễ bị lỗi encoding)."""

import json

from netauto.core.report import ReportGenerator


def test_bao_cao_ghi_duoc_tieng_viet(tmp_path):
    results = [{"device": "R1", "host": "10.0.0.1", "success": False,
                "error": "Không kết nối được thiết bị"}]
    report = ReportGenerator(tmp_path)

    json_path = report.to_json(results, prefix="check")
    html_path = report.to_html(results, prefix="check")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["error"] == "Không kết nối được thiết bị"
    assert "Không kết nối được thiết bị" in html_path.read_text(encoding="utf-8")
