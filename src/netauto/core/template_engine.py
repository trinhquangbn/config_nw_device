"""Lớp bọc (wrapper) đơn giản quanh Jinja2 để render template cấu hình."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from netauto.core.exceptions import TemplateRenderError


class TemplateEngine:
    def __init__(self, templates_dir="templates_config"):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,  # báo lỗi ngay nếu thiếu biến, tránh sinh cấu hình sai
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name, context):
        """Render template với dữ liệu context, trả về danh sách các dòng lệnh
        (bỏ dòng trống và dòng chú thích bắt đầu bằng '!' hoặc '#')."""
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
        except TemplateError as exc:
            raise TemplateRenderError(f"Lỗi render template {template_name}: {exc}") from exc

        return [
            line.rstrip()
            for line in rendered.splitlines()
            if line.strip() and not line.strip().startswith(("!", "#"))
        ]

    def list_templates(self):
        return sorted(p.name for p in self.templates_dir.glob("*.j2"))

    def get_description(self, template_name):
        """Lấy phần chú thích ở đầu template (các dòng bắt đầu bằng '!'),
        thường ghi template dùng để làm gì và cần những biến nào.
        Dừng lại ở dòng lệnh đầu tiên hoặc ở dòng chỉ có '!'."""
        lines = []
        text = (self.templates_dir / template_name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.startswith("!") or line.strip() == "!":
                break
            lines.append(line[1:].strip())  # bỏ dấu '!' ở đầu dòng
        return "\n".join(lines)
