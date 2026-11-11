"""Thao tác nghiệp vụ. Mọi lần ghi đều kiểm tra vai trò, chủ việc và trạng thái mới nhất trên Sheet.

Nguyên tắc: ghi Sheet trước, gửi Telegram sau. Telegram lỗi không hủy thao tác
(trừ ảnh chứng minh, vì Telegram là nơi duy nhất giữ ảnh).
"""
import re
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

import config
import db
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


# --- Thao tác của nhân viên ---

_PNG, _JPG = b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"
_LINK = re.compile(r"https?://\S+")


def _doc_viec(store, id_viec: str) -> dict:
    """Đọc lại dòng việc mới nhất từ Sheet, tránh bấm hai lần hoặc thao tác trên dữ liệu cũ."""
    task = store.get_task(id_viec)
    if task is None:
        raise ServiceError(f"Không tìm thấy việc {id_viec}. Có thể việc đã bị xóa trên Sheet, hãy bấm Làm mới.")
    return task


def _chi_nguoi_nhan(user: dict, task: dict) -> None:
    if not _la_nhan_vien(user) or task[config.COL_NGUOI_NHAN] != user[config.COL_ID_NV]:
        raise PermissionDenied("Chỉ nhân viên được giao việc này mới được thực hiện thao tác.")


def _can_trang_thai(task: dict, cho_phep: list[str]) -> None:
    hien_tai = task[config.COL_TRANG_THAI]
    if hien_tai not in cho_phep:
        raise InvalidState(
            f"Việc đang ở trạng thái \"{hien_tai}\" nên không thực hiện được thao tác này. Hãy bấm Làm mới.")


def start_task(store, user: dict, id_viec: str) -> Result:
    task = _doc_viec(store, id_viec)
    _chi_nguoi_nhan(user, task)
    _can_trang_thai(task, [config.TT_MOI_GIAO, config.TT_LAM_LAI])
    thay_doi = {config.COL_TRANG_THAI: config.TT_DANG_LAM}
    store.update_task(id_viec, thay_doi)
    return Result({**task, **thay_doi}, True)


def submit_task(store, notifier, user: dict, id_viec: str, *, link: str | None = None,
                photo: bytes | None = None, photo_name: str | None = None, today: date) -> Result:
    task = _doc_viec(store, id_viec)
    _chi_nguoi_nhan(user, task)
    _can_trang_thai(task, [config.TT_DANG_LAM, config.TT_LAM_LAI])

    link = (link or "").strip()
    co_anh = photo is not None
    if link and co_anh:
        raise InvalidInput("Chỉ chọn một cách chứng minh: dán link hoặc tải ảnh.")
    if not link and not co_anh:
        raise InvalidInput("Bắt buộc có chứng minh: dán link hoặc tải ảnh.")
    if link and not _LINK.fullmatch(link):
        raise InvalidInput("Link phải bắt đầu bằng http:// hoặc https:// và không có khoảng trắng.")
    if co_anh:
        if not (photo.startswith(_PNG) or photo.startswith(_JPG)):
            raise InvalidInput("Ảnh phải là file JPG hoặc PNG.")
        if len(photo) > config.ANH_MAX_BYTES:
            raise InvalidInput(f"Ảnh không được lớn hơn {config.ANH_MAX_BYTES // (1024 * 1024)} MB.")

    try:
        chat_ql = find_manager(store.employees())[config.COL_CHAT_ID]
    except ServiceError:
        chat_ql = ""
    ten_nv = user.get(config.COL_TEN, user[config.COL_ID_NV])

    if co_anh:
        # Telegram là nơi duy nhất giữ ảnh: gửi được rồi mới chuyển trạng thái
        file_id = notifier.send_photo(chat_ql, photo, photo_name or "chung-minh.jpg",
                                      tin.msg_t3(task, ten_nv, None))
        if not file_id:
            raise ServiceError(
                "Chưa gửi được ảnh qua Telegram (quản lý chưa có Telegram hoặc đường truyền lỗi). "
                "Việc chưa được báo cáo. Hãy thử lại hoặc dán link thay thế.")
        chung_minh, da_gui = config.TG_PREFIX + file_id, True
    else:
        chung_minh, da_gui = link, None

    thay_doi = {
        config.COL_TRANG_THAI: config.TT_CHO_DUYET,
        config.COL_LINK: chung_minh,
        config.COL_NGAY_HOAN_THANH: today.isoformat(),
    }
    store.update_task(id_viec, thay_doi)
    if da_gui is None:
        da_gui = notifier.send_message(chat_ql, tin.msg_t3(task, ten_nv, link))    # T3
    return Result({**task, **thay_doi}, da_gui)


# --- Thao tác của quản lý ---

def _loi_o(task: dict, cot: str, mong_doi: str) -> ServiceError:
    return ServiceError(
        f"Ô {cot} của việc {task[config.COL_ID_VIEC]} đang là \"{task[cot]}\", cần {mong_doi}. "
        f"Hãy sửa trên Sheet rồi bấm Làm mới.")


def _doc_ngay(task: dict, cot: str) -> date:
    try:
        return date.fromisoformat(task[cot].strip())
    except ValueError:
        raise _loi_o(task, cot, "ngày dạng YYYY-MM-DD") from None


def _doc_trong_so(task: dict) -> int:
    try:
        trong_so = int(task[config.COL_TRONG_SO].strip())
    except ValueError:
        trong_so = None
    if trong_so is None or not config.TRONG_SO_MIN <= trong_so <= config.TRONG_SO_MAX:
        raise _loi_o(task, config.COL_TRONG_SO,
                     f"số nguyên từ {config.TRONG_SO_MIN} đến {config.TRONG_SO_MAX}")
    return trong_so


def _chat_nguoi_nhan(store, task: dict) -> str:
    """Chat ID của người nhận việc; chuỗi rỗng nếu không tra được (việc đã lưu thì không báo lỗi nữa)."""
    try:
        nguoi = _nhan_su(store.employees(), task[config.COL_NGUOI_NHAN])
    except db.StoreError:
        return ""
    return nguoi[config.COL_CHAT_ID] if nguoi else ""


def _ghi_kpi_quy(store, id_nv: str, today: date) -> bool:
    """Ghi KPI quý hiện tại của một nhân viên vào bảng nhân sự (D1-A). False nếu ghi lỗi."""
    try:
        tasks = store.tasks()
        cua_nv = tasks[(tasks[config.COL_NGUOI_NHAN] == id_nv)
                       & (tasks[config.COL_QUY] == kpi.quarter_of(today))]
        gia_tri = kpi.quarter_kpi(cua_nv)
        store.update_employee(id_nv, {config.COL_KPI_QUY: "" if gia_tri is None else str(gia_tri)})
        return True
    except db.StoreError:
        return False


def approve_task(store, notifier, user: dict, id_viec: str, *, stars: int, today: date) -> Result:
    task = _doc_viec(store, id_viec)
    _chi_quan_ly(user)
    _can_trang_thai(task, [config.TT_CHO_DUYET])
    if isinstance(stars, bool) or not isinstance(stars, int) or stars not in config.H2_THEO_SAO:
        raise InvalidInput("Bắt buộc chấm từ 1 đến 5 sao trước khi duyệt.")

    trong_so = _doc_trong_so(task)
    tre = kpi.days_late(_doc_ngay(task, config.COL_HAN_CHOT), _doc_ngay(task, config.COL_NGAY_HOAN_THANH))
    diem = kpi.task_score(trong_so, tre, stars)

    thay_doi = {
        config.COL_TRANG_THAI: config.TT_HOAN_THANH,
        config.COL_SAO: str(stars),
        config.COL_DIEM: str(diem),
    }
    store.update_task(id_viec, thay_doi)
    kpi_saved = _ghi_kpi_quy(store, task[config.COL_NGUOI_NHAN], today)
    da_gui = notifier.send_message(_chat_nguoi_nhan(store, task), tin.msg_t4_duyet(task, stars, diem))   # T4
    return Result({**task, **thay_doi}, da_gui, kpi_saved)


def return_task(store, notifier, user: dict, id_viec: str, *, ly_do: str) -> Result:
    task = _doc_viec(store, id_viec)
    _chi_quan_ly(user)
    _can_trang_thai(task, [config.TT_CHO_DUYET])
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise InvalidInput("Bắt buộc ghi lý do khi trả lại.")

    thay_doi = {config.COL_TRANG_THAI: config.TT_LAM_LAI, config.COL_GHI_CHU_QL: ly_do}
    store.update_task(id_viec, thay_doi)
    da_gui = notifier.send_message(_chat_nguoi_nhan(store, task), tin.msg_t4_tra_lai(task, ly_do))       # T4
    return Result({**task, **thay_doi}, da_gui)
