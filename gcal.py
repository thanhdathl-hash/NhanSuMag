"""Google Calendar: tạo và xóa sự kiện trên lịch mà từng người đã chia sẻ cho service account.

Giống notifier.py: không ném lỗi ra ngoài, chỉ trả thành công hay thất bại, mỗi lần gọi tối đa 10 giây.
Mã sự kiện được suy ra từ mã việc hoặc mã lịch, nên đẩy lại không tạo sự kiện trùng.
"""
import hashlib
from datetime import date, datetime, time, timedelta
from urllib.parse import quote

import google.auth.exceptions
import requests

import config

_API = "https://www.googleapis.com/calendar/v3/calendars"
_PHAM_VI = ["https://www.googleapis.com/auth/calendar.events"]
_TIMEOUT = 10
_LOI = (requests.RequestException, google.auth.exceptions.GoogleAuthError, ValueError, TypeError, AttributeError)
_TOM_TAT_TOI_DA, _MO_TA_TOI_DA = 1024, 8000
_FREQ = {config.LAP_NGAY: "DAILY", config.LAP_TUAN: "WEEKLY"}
_GIO_VN_LECH_UTC = timedelta(hours=7)     # Việt Nam không đổi giờ mùa hè


def event_id(tien_to: str, ma: str) -> str:
    """Mã sự kiện hợp lệ với Google (chữ thường a-v và chữ số), ổn định theo mã việc hoặc mã lịch."""
    return tien_to + hashlib.sha1(f"{tien_to}:{ma}".encode()).hexdigest()[:24]


class GoogleCalendar:
    def __init__(self, session):
        """`session` là google.auth.transport.requests.AuthorizedSession; None nếu chưa cấu hình được."""
        self._session = session

    def _url(self, calendar_id: str) -> str:
        return f"{_API}/{quote(calendar_id.strip(), safe='')}/events"

    def add_event(self, calendar_id: str, ev_id: str, summary: str, description: str, ngay: date,
                  gio_bat_dau: time | None = None, gio_ket_thuc: time | None = None,
                  lap: str | None = None, lap_den: date | None = None) -> bool:
        """Tạo sự kiện. Không có giờ bắt đầu thì là sự kiện cả ngày. Đã tồn tại cũng tính là thành công."""
        if self._session is None or not (calendar_id or "").strip():
            return False
        body = {"id": ev_id, "summary": summary[:_TOM_TAT_TOI_DA], "description": description[:_MO_TA_TOI_DA]}
        if gio_bat_dau is None:
            body["start"] = {"date": ngay.isoformat()}
            body["end"] = {"date": (ngay + timedelta(days=1)).isoformat()}      # ngày kết thúc không tính
        else:
            bat_dau = datetime.combine(ngay, gio_bat_dau)
            ket_thuc = datetime.combine(ngay, gio_ket_thuc) if gio_ket_thuc else bat_dau + timedelta(hours=1)
            body["start"] = {"dateTime": bat_dau.isoformat(timespec="seconds"), "timeZone": config.TZ}
            body["end"] = {"dateTime": ket_thuc.isoformat(timespec="seconds"), "timeZone": config.TZ}
        if lap in _FREQ and lap_den is not None:
            if gio_bat_dau is None:
                den = lap_den.strftime("%Y%m%d")
            else:   # với sự kiện có giờ, UNTIL phải ở giờ UTC: hết ngày lap_den theo giờ Việt Nam
                den = (datetime.combine(lap_den, time(23, 59, 59)) - _GIO_VN_LECH_UTC).strftime("%Y%m%dT%H%M%SZ")
            body["recurrence"] = [f"RRULE:FREQ={_FREQ[lap]};UNTIL={den}"]
        try:
            r = self._session.post(self._url(calendar_id), json=body, timeout=_TIMEOUT)
            return r.status_code in (200, 201, 409)
        except _LOI:
            return False

    def delete_event(self, calendar_id: str, ev_id: str) -> bool:
        """Xóa sự kiện (cả chuỗi nếu là sự kiện lặp). Đã mất sẵn cũng tính là thành công."""
        if self._session is None or not (calendar_id or "").strip():
            return False
        try:
            r = self._session.delete(f"{self._url(calendar_id)}/{ev_id}", timeout=_TIMEOUT)
            return r.status_code in (200, 204, 404, 410)
        except _LOI:
            return False


def from_secrets(secrets) -> GoogleCalendar:
    """Tạo GoogleCalendar từ khóa service account trong secrets. Khóa sai thì app vẫn chạy, chỉ không đẩy được."""
    try:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        info = dict(secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=_PHAM_VI)
        return GoogleCalendar(AuthorizedSession(creds))
    except Exception:   # thiếu khóa, khóa sai định dạng: không đưa nội dung lỗi ra ngoài
        return GoogleCalendar(None)
