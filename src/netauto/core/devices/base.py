"""Lớp cơ sở trừu tượng (Abstract Base Class) cho mọi thiết bị mạng.

File này thể hiện 4 tính chất của lập trình hướng đối tượng:

- Trừu tượng: NetworkDevice khai báo các việc mà thiết bị nào cũng làm
  được (connect, disconnect, send_command, backup_config, push_config...).
  Các phương thức có @abstractmethod thì lớp con bắt buộc phải tự viết.

- Kế thừa: CiscoIOSDevice, AristaEOSDevice, JuniperJunOSDevice, VyOSDevice
  kế thừa từ lớp này (xem các file cùng thư mục).

- Đa hình: chương trình gọi device.backup_config() cho một danh sách thiết
  bị của nhiều hãng mà không cần if/else kiểm tra hãng. Python tự gọi đúng
  phương thức của lớp con.

- Đóng gói: mật khẩu lưu trong thuộc tính __password (2 dấu gạch dưới,
  Python tự đổi tên để bên ngoài không truy cập trực tiếp được). Chỉ đổi
  mật khẩu qua property setter, còn getter luôn trả về chuỗi "********".
"""

from abc import ABC, abstractmethod
from datetime import datetime

from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoAuthenticationException, NetMikoTimeoutException

from netauto.core.exceptions import (
    CommandExecutionError,
    DeviceAuthenticationError,
    DeviceConnectionError,
)
from netauto.core.logger import audit, get_logger


class NetworkDevice(ABC):
    """Lớp cơ sở trừu tượng mô tả một thiết bị mạng bất kỳ."""

    # Các thuộc tính lớp, mỗi lớp con tự gán lại cho đúng hãng của mình.
    NETMIKO_DEVICE_TYPE = "generic"  # tên device_type của Netmiko
    NEEDS_ENABLE = False             # có cần vào chế độ enable không
    # Mẫu thông báo lỗi khi gõ sai lệnh cấu hình (Cisco, Arista).
    # Netmiko sẽ báo lỗi ngay khi kết quả có chứa mẫu này.
    CONFIG_ERROR_PATTERN = r"% Invalid|% Incomplete|% Ambiguous"

    def __init__(self, name, host, username, password, port=22,
                 secret=None, group="default", tags=None):
        self.name = name
        self.host = host
        self.port = port
        self.group = group
        self.tags = tags or []

        # Gán qua property để được kiểm tra giá trị (xem setter bên dưới).
        self.username = username
        self.password = password
        self.__secret = secret or password

        self._session = None  # phiên SSH của Netmiko, None khi chưa kết nối
        self.logger = get_logger()

    # ------------------------------------------------------------------ #
    # Đóng gói: getter / setter cho thông tin đăng nhập
    # ------------------------------------------------------------------ #
    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not value:
            raise ValueError(f"Thiết bị {self.name}: username không được để trống")
        self._username = value

    @property
    def password(self):
        # Không bao giờ trả về mật khẩu thật ra bên ngoài.
        return "********"

    @password.setter
    def password(self, value):
        if not value:
            raise ValueError(f"Thiết bị {self.name}: password không được để trống")
        self.__password = value

    def __repr__(self):
        # Không in mật khẩu khi log hoặc print đối tượng.
        return f"<{self.__class__.__name__} name={self.name} host={self.host}>"

    # ------------------------------------------------------------------ #
    # Context manager: dùng được câu lệnh "with device:"
    # ------------------------------------------------------------------ #
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()
        return False  # không "nuốt" lỗi, để lỗi tiếp tục được xử lý ở ngoài

    # ------------------------------------------------------------------ #
    # Kết nối, ngắt kết nối, gửi lệnh: dùng chung cho mọi hãng
    # ------------------------------------------------------------------ #
    def connect(self):
        """Mở kết nối SSH tới thiết bị bằng Netmiko."""
        try:
            self._session = ConnectHandler(
                device_type=self.NETMIKO_DEVICE_TYPE,
                host=self.host,
                port=self.port,
                username=self._username,
                password=self.__password,
                secret=self.__secret,
            )
        except NetMikoAuthenticationException as exc:
            raise DeviceAuthenticationError(f"Sai thông tin đăng nhập {self.host}: {exc}") from exc
        except NetMikoTimeoutException as exc:
            # Netmiko dùng chung lỗi này cho cả timeout lẫn lỗi SSH (ví dụ thiết bị
            # chỉ hỗ trợ thuật toán mã hóa cũ), nên thông báo ghi cả hai khả năng.
            raise DeviceConnectionError(
                f"Không kết nối được {self.host} (hết thời gian chờ hoặc lỗi SSH): {exc}") from exc
        except Exception as exc:
            raise DeviceConnectionError(f"Không thể kết nối {self.host}: {exc}") from exc

        if self.NEEDS_ENABLE:
            self._session.enable()

        self.logger.info("Đã kết nối tới %s (%s)", self.name, self.host)

    def disconnect(self):
        """Đóng kết nối SSH nếu đang mở."""
        if self._session is None:
            return
        try:
            self._session.disconnect()
        except Exception as exc:
            self.logger.warning("Lỗi khi ngắt kết nối %s: %s", self.name, exc)
        self._session = None
        self.logger.info("Đã ngắt kết nối %s", self.name)

    def is_alive(self):
        """Kiểm tra phiên SSH còn hoạt động không."""
        return self._session is not None and self._session.is_alive()

    def send_command(self, command, use_textfsm=False):
        """Gửi một lệnh show và trả về kết quả.

        use_textfsm=True: Netmiko dùng TextFSM để chuyển kết quả dạng chữ
        thành danh sách dict (nếu có sẵn template cho lệnh đó).
        """
        if self._session is None:
            raise DeviceConnectionError(f"{self.name} chưa được kết nối")
        try:
            return self._session.send_command(command, use_textfsm=use_textfsm, read_timeout=30)
        except Exception as exc:
            raise CommandExecutionError(f"{self.name}: lệnh '{command}' bị lỗi: {exc}") from exc

    def _error_pattern(self, check_errors):
        """Trả về mẫu lỗi cho Netmiko, hoặc chuỗi rỗng nếu không kiểm tra lỗi."""
        return self.CONFIG_ERROR_PATTERN if check_errors else ""

    def send_config_set(self, config_lines, check_errors=True):
        """Gửi danh sách lệnh cấu hình.

        check_errors=True: nếu thiết bị báo sai lệnh thì dừng lại và báo lỗi
        (để BatchOperator biết mà rollback).
        Juniper và VyOS ghi đè hàm này để thêm bước commit.
        """
        if self._session is None:
            raise DeviceConnectionError(f"{self.name} chưa được kết nối")
        return self._session.send_config_set(config_lines,
                                             error_pattern=self._error_pattern(check_errors))

    # ------------------------------------------------------------------ #
    # Các phương thức trừu tượng: lớp con bắt buộc phải viết
    # ------------------------------------------------------------------ #
    @abstractmethod
    def get_running_config(self):
        """Lấy cấu hình đang chạy (running-config) dạng text."""

    @abstractmethod
    def get_facts(self):
        """Lấy thông tin cơ bản của thiết bị, trả về dict."""

    @abstractmethod
    def save_config(self):
        """Lưu cấu hình (write memory, save... tùy hãng)."""

    # ------------------------------------------------------------------ #
    # Phương thức dùng chung, lớp con không cần viết lại
    # ------------------------------------------------------------------ #
    def backup_config(self):
        """Trả về dict gồm cấu hình hiện tại và thời điểm sao lưu."""
        return {
            "device": self.name,
            "host": self.host,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "config": self.get_running_config(),
        }

    def push_config(self, config_lines, save=True, check_errors=True):
        """Áp danh sách lệnh cấu hình, sau đó lưu lại nếu save=True."""
        output = self.send_config_set(config_lines, check_errors)
        if save:
            self.save_config()
        return output

    def execute_task(self, method, *args, user="system", **kwargs):
        """Quy trình chung cho mọi thao tác trên thiết bị:
        kết nối -> gọi method(*args, **kwargs) -> ngắt kết nối, có ghi log.

        Lỗi được bắt ngay tại đây và trả về trong kết quả, để lỗi của một
        thiết bị không làm dừng cả chương trình.

        Ví dụ:
            device.execute_task(device.get_running_config)
            device.execute_task(device.push_config, ["vlan 10"])
        """
        result = {"device": self.name, "host": self.host, "success": False}
        try:
            with self:  # tự connect() khi vào và disconnect() khi ra
                result["data"] = method(*args, **kwargs)
            result["success"] = True
            audit(method.__name__, self.name, user, "OK")
        except Exception as exc:
            result["error"] = str(exc)
            audit(method.__name__, self.name, user, "FAILED", detail=str(exc))
            self.logger.error("Lỗi khi thao tác trên %s: %s", self.name, exc)
        return result
