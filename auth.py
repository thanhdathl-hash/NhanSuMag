"""Xác thực (D2): ID hoặc SĐT cộng mã PIN, khóa tạm khi nhập sai nhiều lần."""
import hmac
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

import config

_SO_KHOA_TOI_DA = 1000   # chặn bộ đếm phình ra khi có người thử hàng loạt ID


def normalize_phone(s: str) -> str:
    """Chuẩn hóa SĐT về dạng 0xxxxxxxxx để so sánh."""
    s = re.sub(r"[\s.\-()]", "", str(s))
    if s.startswith("+84"):
        return "0" + s[3:]
    if s.startswith("84") and len(s) == 11:
        return "0" + s[2:]
    if len(s) == 9 and s.isdigit() and not s.startswith("0"):   # Sheet nuốt số 0 đầu
        return "0" + s
    return s


class LoginGuard:
    """Đếm số lần nhập sai liên tiếp theo tài khoản, nằm trong bộ nhớ tiến trình."""

    def __init__(self, max_fails: int = config.SO_LAN_SAI_TOI_DA, lock_minutes: int = config.KHOA_PHUT):
        self._max = max_fails
        self._lock_for = timedelta(minutes=lock_minutes)
        self._state: dict[str, tuple[int, datetime | None]] = {}   # khóa -> (số lần sai, khóa đến)
        self._mutex = threading.Lock()

    def is_locked(self, key: str, now: datetime) -> bool:
        with self._mutex:
            _, den = self._state.get(key, (0, None))
            if den is None:
                return False
            if now < den:
                return True
            del self._state[key]    # hết hạn khóa: bộ đếm về 0
            return False

    def record_failure(self, key: str, now: datetime) -> None:
        with self._mutex:
            if len(self._state) >= _SO_KHOA_TOI_DA and key not in self._state:
                self._state = {k: v for k, v in self._state.items() if v[1] is not None and now < v[1]}
            so_lan = self._state.get(key, (0, None))[0] + 1
            den = now + self._lock_for if so_lan >= self._max else None
            self._state[key] = (so_lan, den)

    def reset(self, key: str) -> None:
        with self._mutex:
            self._state.pop(key, None)


@dataclass
class AuthResult:
    user: dict | None     # các cột nhân sự trừ mã PIN
    error: str | None


def _tim_tai_khoan(employees: pd.DataFrame, ident: str) -> dict | None:
    theo_id = employees[employees[config.COL_ID_NV].str.strip().str.casefold() == ident.casefold()]
    if len(theo_id) == 1:
        return theo_id.iloc[0].to_dict()
    sdt = normalize_phone(ident)
    if not sdt.isdigit():
        return None
    theo_sdt = employees[employees[config.COL_SDT].map(normalize_phone) == sdt]
    # Trùng SĐT thì không biết là ai: coi như không tìm thấy
    return theo_sdt.iloc[0].to_dict() if len(theo_sdt) == 1 else None


def authenticate(employees: pd.DataFrame, identifier: str, pin: str,
                 guard: LoginGuard, now: datetime) -> AuthResult:
    """Trả về người dùng nếu đúng, ngược lại một thông báo lỗi không tiết lộ ID có tồn tại hay không."""
    ident = (identifier or "").strip()
    pin = (pin or "").strip()
    if not ident:
        return AuthResult(None, config.MSG_DANG_NHAP_SAI)

    tk = _tim_tai_khoan(employees, ident)
    # ID không tồn tại cũng được đếm và khóa như ID thật
    khoa = tk[config.COL_ID_NV] if tk else "?" + normalize_phone(ident).casefold()
    if guard.is_locked(khoa, now):
        return AuthResult(None, config.MSG_TAI_KHOAN_KHOA)

    pin_luu = str(tk[config.COL_MA_PIN]).strip() if tk else ""
    dung = bool(tk and pin and pin_luu) and hmac.compare_digest(pin_luu.encode(), pin.encode())
    if not dung:
        guard.record_failure(khoa, now)
        return AuthResult(None, config.MSG_DANG_NHAP_SAI)

    guard.reset(khoa)
    return AuthResult({k: v for k, v in tk.items() if k != config.COL_MA_PIN}, None)
