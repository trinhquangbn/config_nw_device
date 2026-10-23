"""Sinh báo cáo kết quả thực thi (JSON/HTML) - yêu cầu chức năng số 6."""

import json
from datetime import datetime
from pathlib import Path


class ReportGenerator:
    def __init__(self, report_dir="data/reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _stamp(self, prefix, ext):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.report_dir / f"{prefix}_{ts}.{ext}"

    def to_json(self, results, prefix="report"):
        path = self._stamp(prefix, "json")
        # encoding="utf-8": Windows mặc định dùng cp1252, không ghi được tiếng Việt.
        path.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def to_html(self, results, prefix="report", title="Báo cáo NetAuto"):
        rows_html = []
        for row in results:
            status = "OK" if row.get("success") else "FAILED"
            css_class = "ok" if row.get("success") else "fail"
            rows_html.append(
                f"<tr class='{css_class}'><td>{row.get('device', '')}</td>"
                f"<td>{row.get('host', '')}</td><td>{status}</td>"
                f"<td>{row.get('error', '')}</td></tr>"
            )
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:14px}}
th{{background:#f2f2f2}}
tr.ok td:nth-child(3){{color:#0a7d28;font-weight:bold}}
tr.fail td:nth-child(3){{color:#c1121f;font-weight:bold}}
</style></head><body>
<h2>{title}</h2>
<p>Thời gian tạo: {datetime.now().isoformat(timespec='seconds')}</p>
<table><tr><th>Thiết bị</th><th>Host</th><th>Trạng thái</th><th>Chi tiết lỗi</th></tr>
{''.join(rows_html)}
</table></body></html>"""
        path = self._stamp(prefix, "html")
        path.write_text(html, encoding="utf-8")
        return path
