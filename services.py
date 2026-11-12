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
    warning: str | None = None   # đã lưu, nhưng có điều người dùng cần biết


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

    da_co = store.tasks()
    # Chặn bấm "Giao việc" hai lần: cùng tên, cùng người, cùng hạn, giao trong hôm nay và chưa ai bắt đầu
    trung = da_co[(da_co[config.COL_TEN_VIEC] == ten_viec) & (da_co[config.COL_NGUOI_NHAN] == nguoi_nhan)
                  & (da_co[config.COL_HAN_CHOT] == han_chot.isoformat())
                  & (da_co[config.COL_NGAY_GIAO] == today.isoformat())
                  & (da_co[config.COL_TRANG_THAI] == config.TT_MOI_GIAO)]
    if not trung.empty:
        raise InvalidInput("Việc này vừa được giao hôm nay cho cùng người nhận với cùng hạn chót. "
                           "Nếu muốn giao thêm một việc giống vậy, hãy đổi tên việc.")

    task = {k: "" for k in config.VIEC_COLS}
    task.update({
        config.COL_ID_VIEC: _sinh_id(set(da_co[config.COL_ID_VIEC])),
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

    loi_ql = None
    try:
        chat_ql = find_manager(store.employees())[config.COL_CHAT_ID]
    except ServiceError as e:
        chat_ql, loi_ql = "", str(e)
    ten_nv = user.get(config.COL_TEN, user[config.COL_ID_NV])

    if co_anh:
        if loi_ql:
            raise ServiceError(f"{loi_ql} Vì vậy chưa gửi được ảnh và việc chưa được báo cáo. "
                               "Hãy báo quản lý, hoặc dán link thay thế.")
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
    if loi_ql:
        return Result({**task, **thay_doi}, False,
                      warning=f"Đã lưu, nhưng chưa báo được cho quản lý qua Telegram. {loi_ql}")
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
        tasks = prepare_tasks(store.tasks())
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


# --- Số liệu cho giao diện (chỉ đọc) ---

_QUY = re.compile(r"\d{4}-Q[1-4]")


def employee_kpi(tasks: pd.DataFrame, id_nv: str, quy: str) -> tuple[float | None, int, int]:
    """(KPI quý hoặc None nếu chưa có việc, số việc đã hoàn thành, tổng số việc)."""
    cua_nv = tasks[(tasks[config.COL_NGUOI_NHAN] == id_nv) & (tasks[config.COL_QUY] == quy)]
    return (kpi.quarter_kpi(cua_nv), *kpi.quarter_progress(cua_nv))


def kpi_table(tasks: pd.DataFrame, employees: pd.DataFrame, quy: str) -> pd.DataFrame:
    """KPI quý của từng nhân viên (không gồm quản lý)."""
    cols = [config.COL_ID_NV, config.COL_TEN, config.KQ_KPI, config.KQ_HOAN_THANH, config.KQ_TONG_VIEC]
    dong = []
    for _, nv in employees[employees[config.COL_ROLE] == config.ROLE_NHAN_VIEN].iterrows():
        diem, xong, tong = employee_kpi(tasks, nv[config.COL_ID_NV], quy)
        dong.append([nv[config.COL_ID_NV], nv[config.COL_TEN], diem, xong, tong])
    df = pd.DataFrame(dong, columns=cols)
    df[config.KQ_KPI] = pd.Series([d[2] for d in dong], dtype=object)   # giữ None, không đổi thành NaN
    return df


def _ngay_hoac_none(s: str) -> date | None:
    try:
        return date.fromisoformat(s.strip())
    except ValueError:
        return None


def prepare_tasks(tasks: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng việc trước khi dùng, vì quản lý có thể sửa tay trên Sheet.

    - Bỏ dòng thiếu mã việc và dòng trùng mã (giữ dòng đầu, cũng là dòng mà thao tác ghi sẽ sửa).
    - Quý và tháng tính lại từ hạn chót (spec mục 5); chỉ dùng ô trên Sheet khi hạn chót hỏng.
    """
    df = tasks[tasks[config.COL_ID_VIEC] != ""].drop_duplicates(subset=config.COL_ID_VIEC, keep="first").copy()
    han = [_ngay_hoac_none(s) for s in df[config.COL_HAN_CHOT]]
    df[config.COL_QUY] = [kpi.quarter_of(d) if d else cu for d, cu in zip(han, df[config.COL_QUY])]
    df[config.COL_THANG] = [kpi.month_of(d) if d else cu for d, cu in zip(han, df[config.COL_THANG])]
    return df


def sheet_warnings(tasks: pd.DataFrame, employees: pd.DataFrame) -> list[str]:
    """Những chỗ dữ liệu trên Sheet cần quản lý sửa. Nhận bảng việc CHƯA qua prepare_tasks."""
    canh_bao = []
    so_ql = int((employees[config.COL_ROLE] == config.ROLE_QUAN_LY).sum())
    if so_ql != 1:
        canh_bao.append(
            f"Bảng {config.SHEET_NHAN_SU} phải có đúng một dòng {config.COL_ROLE} = {config.ROLE_QUAN_LY}, "
            f"hiện có {so_ql}. Thông báo cho quản lý và ảnh chứng minh sẽ không gửi được.")
    ids = tasks[config.COL_ID_VIEC]
    thieu = int((ids == "").sum())
    if thieu:
        canh_bao.append(f"Bảng {config.SHEET_VIEC} có {thieu} dòng thiếu {config.COL_ID_VIEC}; "
                        "các dòng này không hiện trong app. Hãy điền mã riêng cho từng dòng hoặc xóa dòng.")
    trung = sorted(set(ids[(ids != "") & ids.duplicated()]))
    if trung:
        canh_bao.append(f"Bảng {config.SHEET_VIEC} có mã việc bị trùng: {', '.join(trung)}. "
                        "App chỉ dùng dòng đầu tiên của mỗi mã. Hãy đổi mã hoặc xóa dòng thừa.")
    la = tasks[(ids != "") & ~tasks[config.COL_TRANG_THAI].isin(config.TRANG_THAI)]
    for _, v in la.iterrows():
        canh_bao.append(f"Việc {v[config.COL_ID_VIEC]} có {config.COL_TRANG_THAI} là \"{v[config.COL_TRANG_THAI]}\", "
                        f"không thuộc: {', '.join(config.TRANG_THAI)}. Nhân viên sẽ không thấy việc này.")
    return canh_bao


def overdue_tasks(tasks: pd.DataFrame, today: date) -> pd.DataFrame:
    """Việc đã qua hạn mà nhân viên chưa nộp. Dòng có hạn chót hỏng bị bỏ qua."""
    han = tasks[config.COL_HAN_CHOT].map(_ngay_hoac_none)
    qua_han = han.map(lambda d: d is not None and d < today).astype(bool)
    return tasks[qua_han & tasks[config.COL_TRANG_THAI].isin(config.TT_CHUA_NOP)]


def status_counts(tasks: pd.DataFrame) -> dict[str, int]:
    dem = tasks[config.COL_TRANG_THAI].value_counts()
    return {tt: int(dem.get(tt, 0)) for tt in config.TRANG_THAI}


def quarters(tasks: pd.DataFrame, today: date) -> list[str]:
    """Các quý có việc, cộng quý hiện tại, mới nhất trước."""
    co = {q for q in tasks[config.COL_QUY] if _QUY.fullmatch(q)}
    return sorted(co | {kpi.quarter_of(today)}, reverse=True)


def current_quarter(today: date) -> str:
    return kpi.quarter_of(today)


# --- Bảng điều khiển: bốn nhóm việc, khối lượng theo nhân viên, lịch hạn chót ---

def task_group(trang_thai: str, han_chot: str, today: date) -> str | None:
    """Xếp một việc vào đúng một nhóm của bảng điều khiển. None nếu trạng thái không hợp lệ.

    Quá hạn chỉ tính việc chưa nộp có hạn chót trước hôm nay; hạn chót hỏng thì không kết luận quá hạn.
    """
    if trang_thai == config.TT_HOAN_THANH:
        return config.NHOM_HOAN_THANH
    if trang_thai == config.TT_CHO_DUYET:
        return config.NHOM_CHO_DUYET
    if trang_thai in config.TT_CHUA_NOP:
        han = _ngay_hoac_none(han_chot)
        return config.NHOM_QUA_HAN if han is not None and han < today else config.NHOM_DANG_LAM
    return None


def _nhom_cua_bang(tasks: pd.DataFrame, today: date) -> list:
    return [task_group(tt, han, today)
            for tt, han in zip(tasks[config.COL_TRANG_THAI], tasks[config.COL_HAN_CHOT])]


def dashboard_counts(tasks: pd.DataFrame, today: date) -> dict[str, int]:
    """Số việc theo bốn nhóm, đủ khóa theo thứ tự config.NHOM_VIEC."""
    nhom = _nhom_cua_bang(tasks, today)
    return {n: nhom.count(n) for n in config.NHOM_VIEC}


def workload_table(tasks: pd.DataFrame, employees: pd.DataFrame, today: date) -> pd.DataFrame:
    """Số việc của từng nhân viên theo bốn nhóm. Cột: ID_NV, Ten, rồi từng nhóm."""
    dong = []
    for _, nv in employees[employees[config.COL_ROLE] == config.ROLE_NHAN_VIEN].iterrows():
        dem = dashboard_counts(tasks[tasks[config.COL_NGUOI_NHAN] == nv[config.COL_ID_NV]], today)
        dong.append([nv[config.COL_ID_NV], nv[config.COL_TEN], *dem.values()])
    return pd.DataFrame(dong, columns=[config.COL_ID_NV, config.COL_TEN, *config.NHOM_VIEC])


def calendar_events(tasks: pd.DataFrame, year: int, month: int, today: date) -> dict[date, list[dict]]:
    """Các việc có hạn chót trong tháng, gom theo ngày. Mỗi việc là dòng việc kèm khóa "nhom"."""
    lich: dict[date, list[dict]] = {}
    for v in tasks.to_dict("records"):
        han = _ngay_hoac_none(v[config.COL_HAN_CHOT])
        nhom = task_group(v[config.COL_TRANG_THAI], v[config.COL_HAN_CHOT], today)
        if han is None or nhom is None or (han.year, han.month) != (year, month):
            continue
        lich.setdefault(han, []).append({**v, "nhom": nhom})
    for ds in lich.values():
        ds.sort(key=lambda e: e[config.COL_TEN_VIEC])
    return lich


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Lùi hoặc tiến một số tháng, trả (năm, tháng)."""
    so = year * 12 + (month - 1) + delta
    return so // 12, so % 12 + 1


# --- Khối "Việc cần xử lý" ---

def todo_groups(tasks: pd.DataFrame, user: dict, today: date) -> list[dict]:
    """Những việc người dùng cần để ý ngay, tính trực tiếp từ bảng việc (đã lọc theo quyền).

    Trả về danh sách nhóm không rỗng, theo thứ tự gấp dần: {"ma", "nhan", "viec": [dòng việc]}.
    Với nhân viên, mỗi việc chỉ nằm ở một nhóm, nhóm gấp nhất.
    """
    nhom: dict[str, list[dict]] = {}
    la_ql = _la_quan_ly(user)
    for v in tasks.to_dict("records"):
        tt = v[config.COL_TRANG_THAI]
        han = _ngay_hoac_none(v[config.COL_HAN_CHOT])
        chua_nop = tt in config.TT_CHUA_NOP
        con = None if han is None else (han - today).days       # số ngày còn lại tới hạn
        if la_ql and tt == config.TT_CHO_DUYET:
            ma = config.CXL_CHO_DUYET
        elif chua_nop and con is not None and con < 0:
            ma = config.CXL_QUA_HAN
        elif not la_ql and tt == config.TT_LAM_LAI:
            ma = config.CXL_LAM_LAI
        elif chua_nop and con == 0:
            ma = config.CXL_HOM_NAY
        elif not la_ql and chua_nop and con is not None and con <= config.SO_NGAY_SAP_DEN_HAN:
            ma = config.CXL_SAP_DEN_HAN
        elif not la_ql and tt == config.TT_MOI_GIAO:
            ma = config.CXL_MOI_GIAO
        else:
            continue
        nhom.setdefault(ma, []).append(v)
    thu_tu = ([config.CXL_CHO_DUYET, config.CXL_QUA_HAN, config.CXL_HOM_NAY] if la_ql else
              [config.CXL_QUA_HAN, config.CXL_LAM_LAI, config.CXL_HOM_NAY, config.CXL_SAP_DEN_HAN, config.CXL_MOI_GIAO])
    return [{"ma": ma, "nhan": config.CXL_NHAN[ma],
             "viec": sorted(nhom[ma], key=lambda v: (v[config.COL_HAN_CHOT], v[config.COL_TEN_VIEC]))}
            for ma in thu_tu if ma in nhom]


def todo_count(groups: list[dict]) -> int:
    return sum(len(g["viec"]) for g in groups)
