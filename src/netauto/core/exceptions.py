"""Các lớp Exception (ngoại lệ) riêng của chương trình.

Tách riêng từng loại lỗi để chương trình biết chính xác lỗi gì đã xảy ra
(kết nối, sai mật khẩu, lệnh sai, cấu hình lỗi...) và xử lý phù hợp, thay
vì chỉ bắt Exception chung chung.
"""


class NetAutoError(Exception):
    """Lớp cha cho mọi lỗi của NetAuto."""


class InventoryError(NetAutoError):
    """Lỗi liên quan tới file/dữ liệu inventory (thiếu, sai định dạng...)."""


class DeviceConnectionError(NetAutoError):
    """Không kết nối được tới thiết bị (timeout, sai địa chỉ...)."""


class DeviceAuthenticationError(NetAutoError):
    """Sai tài khoản/mật khẩu khi đăng nhập thiết bị."""


class CommandExecutionError(NetAutoError):
    """Lệnh show/exec thực thi bị lỗi."""


class ConfigPushError(NetAutoError):
    """Áp cấu hình lên thiết bị bị lỗi."""


class TemplateRenderError(NetAutoError):
    """Render template Jinja2 bị lỗi (thiếu biến, sai cú pháp...)."""
