"""Thao tác nghiệp vụ. Mọi lần ghi đều kiểm tra vai trò, chủ việc và trạng thái mới nhất trên Sheet.

Nguyên tắc: ghi Sheet trước, gửi Telegram sau. Telegram lỗi không hủy thao tác
(trừ ảnh chứng minh, vì Telegram là nơi duy nhất giữ ảnh).
"""
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

import config
import kpi
import notifier as tin


class ServiceError(Exception):
    """Lỗi nghiệp vụ. Thông điệp bằng tiếng Việt, hiện thẳng lên giao diện."""


class PermissionDenied(ServiceError):
    pass


class InvalidState(ServiceError):
    pass


class InvalidInput(ServiceError):
    pass


@dataclass
class Result:
    task: dict              # dòng việc sau khi ghi
    notified: bool          # False: đã lưu nhưng chưa gửi được Telegram
    kpi_saved: bool = True  # False: đã duyệt nhưng chưa ghi được KPI quý vào bảng nhân sự


# --- Thời gian ---

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hom_nay() -> date:
    """Hôm nay theo giờ Việt Nam, không phụ thuộc múi giờ của máy chủ."""
    return _now_utc().astimezone(ZoneInfo(config.TZ)).date()


# --- Dùng chung ---

def _la_quan_ly(user: dict) -> bool:
    return user.get(config.COL_ROLE) == config.ROLE_QUAN_LY


def _la_nhan_vien(user: dict) -> bool:
    return user.get(config.COL_ROLE) == config.ROLE_NHAN_VIEN


def _chi_quan_ly(user: dict) -> None:
    if not _la_quan_ly(user):
        raise PermissionDenied("Chỉ quản lý mới được thực hiện thao tác này.")


def _nhan_su(employees: pd.DataFrame, id_nv: str) -> dict | None:
    khop = employees[employees[config.COL_ID_NV] == id_nv]
    return None if khop.empty else khop.iloc[0].to_dict()


def find_manager(employees: pd.DataFrame) -> dict:
    """Dòng quản lý duy nhất trong bảng nhân sự."""
    ql = employees[employees[config.COL_ROLE] == config.ROLE_QUAN_LY]
    if len(ql) != 1:
        raise ServiceError(
            f"Bảng {config.SHEET_NHAN_SU} phải có đúng một dòng {config.COL_ROLE} = "
            f"{config.ROLE_QUAN_LY}, hiện có {len(ql)}.")
    return ql.iloc[0].to_dict()


def visible_tasks(tasks: pd.DataFrame, user: dict) -> pd.DataFrame:
    """Quản lý thấy tất cả; nhân viên chỉ thấy việc của mình. Lọc trước khi đưa ra giao diện."""
    if _la_quan_ly(user):
        return tasks
    if _la_nhan_vien(user):
        return tasks[tasks[config.COL_NGUOI_NHAN] == user[config.COL_ID_NV]]
    return tasks.iloc[0:0]


# --- Tạo việc ---

def _sinh_id(da_co: set[str]) -> str:
    while True:
        id_viec = "V-" + secrets.token_hex(4)
        if id_viec not in da_co:
            return id_viec


def create_task(store, notifier, user: dict, *, ten_viec: str, mo_ta: str, nguoi_nhan: str,
                han_chot: date, trong_so: int, today: date) -> Result:
    _chi_quan_ly(user)
    ten_viec = (ten_viec or "").strip()
    mo_ta = (mo_ta or "").strip()
    if not ten_viec:
        raise InvalidInput("Chưa nhập tên việc.")
    if isinstance(trong_so, bool) or not isinstance(trong_so, int) \
            or not config.TRONG_SO_MIN <= trong_so <= config.TRONG_SO_MAX:
        raise InvalidInput(f"Trọng số phải là số nguyên từ {config.TRONG_SO_MIN} đến {config.TRONG_SO_MAX}.")
    if isinstance(han_chot, datetime):
        han_chot = han_chot.date()
    if not isinstance(han_chot, date):
        raise InvalidInput("Chưa chọn hạn chót.")

    nguoi = _nhan_su(store.employees(), nguoi_nhan) if nguoi_nhan else None
    if nguoi is None or nguoi[config.COL_ROLE] != config.ROLE_NHAN_VIEN:
        raise InvalidInput("Người nhận phải là một nhân viên trong danh sách.")

    task = {k: "" for k in config.VIEC_COLS}
    task.update({
        config.COL_ID_VIEC: _sinh_id(set(store.tasks()[config.COL_ID_VIEC])),
        config.COL_TEN_VIEC: ten_viec,
        config.COL_MO_TA: mo_ta,
        config.COL_NGUOI_NHAN: nguoi_nhan,
        config.COL_TRONG_SO: str(trong_so),
        config.COL_NGAY_GIAO: today.isoformat(),
        config.COL_HAN_CHOT: han_chot.isoformat(),
        config.COL_TRANG_THAI: config.TT_MOI_GIAO,
        config.COL_THANG: kpi.month_of(han_chot),
        config.COL_QUY: kpi.quarter_of(han_chot),
    })
    store.append_task(task)
    da_gui = notifier.send_message(nguoi[config.COL_CHAT_ID], tin.msg_t1(task))    # T1
    return Result(task, da_gui)
