"""Giao diện Streamlit. Không ghi thẳng vào Sheet, không gửi Telegram: mọi thao tác đi qua services.py."""
from datetime import datetime, timezone

import streamlit as st

import auth
import config
import db
import notifier
import services

st.set_page_config(page_title="Giao việc và KPI", page_icon="📋", layout="wide")

THU_TU_NHOM = [config.TT_LAM_LAI, config.TT_MOI_GIAO, config.TT_DANG_LAM,
               config.TT_CHO_DUYET, config.TT_HOAN_THANH]


# --- Tài nguyên dùng chung giữa các phiên ---

@st.cache_resource
def get_store():
    store = db.open_store(st.secrets)
    store.check_headers()
    return store


@st.cache_resource
def get_notifier():
    return notifier.Notifier(st.secrets["telegram_bot_token"])


@st.cache_resource
def get_guard():
    return auth.LoginGuard()


@st.cache_data(ttl=config.CACHE_TTL_GIAY)
def load_employees():
    return get_store().employees()


@st.cache_data(ttl=config.CACHE_TTL_GIAY)
def load_templates():
    return get_store().templates()


@st.cache_data(ttl=config.CACHE_TTL_GIAY)
def load_tasks():
    return get_store().tasks()


# --- Thông báo sau thao tác ---

def flash(kieu: str, noi_dung: str) -> None:
    st.session_state.setdefault("flash", []).append((kieu, noi_dung))


def hien_flash() -> None:
    for kieu, noi_dung in st.session_state.pop("flash", []):
        getattr(st, kieu)(noi_dung)


def thuc_hien(ham, *args, **kwargs) -> bool:
    """Gọi một thao tác của services, đổi kết quả thành thông báo. Trả True nếu đã lưu.

    Dùng trong callback của nút bấm: khi lỗi, giá trị người dùng đã nhập vẫn còn nguyên.
    """
    try:
        kq = ham(*args, **kwargs)
    except services.ServiceError as e:
        flash("error", str(e))
        return False
    except db.StoreError:
        flash("error", config.MSG_LOI_SHEET)
        return False
    st.cache_data.clear()
    if not kq.kpi_saved:
        flash("warning", f"Đã duyệt, nhưng cột {config.COL_KPI_QUY} trên Sheet chưa cập nhật được.")
    if kq.notified:
        flash("success", config.MSG_DA_LUU)
    else:
        flash("warning", config.MSG_DA_LUU_CHUA_GUI)
    return True


# --- Đăng nhập ---

def cb_dang_nhap() -> None:
    try:
        nhan_su = load_employees()
    except db.StoreError:
        flash("error", config.MSG_LOI_SHEET)
        return
    kq = auth.authenticate(nhan_su, st.session_state.get("login_id", ""),
                           st.session_state.get("login_pin", ""), get_guard(), datetime.now(timezone.utc))
    st.session_state["login_pin"] = ""
    if kq.user is None:
        flash("error", kq.error)
    else:
        st.session_state["user"] = kq.user
        st.session_state["login_id"] = ""


def cb_dang_xuat() -> None:
    st.session_state.pop("user", None)


def cb_lam_moi() -> None:
    st.cache_data.clear()


def man_hinh_dang_nhap() -> None:
    st.title("📋 Giao việc và KPI")
    with st.form("login_form"):
        st.text_input("ID nhân viên hoặc số điện thoại", key="login_id")
        st.text_input("Mã PIN", type="password", key="login_pin")
        st.form_submit_button("Đăng nhập", key="login_submit", on_click=cb_dang_nhap)


def nguoi_dung_hien_tai(nhan_su) -> dict | None:
    """Lấy lại người dùng từ bảng nhân sự ở mỗi lần chạy: đổi vai trò hay xóa người có hiệu lực ngay."""
    da_luu = st.session_state.get("user")
    if not da_luu:
        return None
    khop = nhan_su[nhan_su[config.COL_ID_NV] == da_luu[config.COL_ID_NV]]
    if len(khop) != 1:
        st.session_state.pop("user", None)
        return None
    user = {k: v for k, v in khop.iloc[0].to_dict().items() if k != config.COL_MA_PIN}
    st.session_state["user"] = user
    return user


# --- Hiển thị một việc ---

def the_viec(v: dict) -> None:
    st.markdown(f"**{v[config.COL_TEN_VIEC]}**")
    st.caption(f"Hạn chót: {v[config.COL_HAN_CHOT]} · Trọng số: {v[config.COL_TRONG_SO]} · "
               f"Mã việc: {v[config.COL_ID_VIEC]}")
    if v[config.COL_MO_TA]:
        st.write(v[config.COL_MO_TA])


# --- Màn hình Nhân viên ---

def cb_bat_dau(id_viec: str) -> None:
    thuc_hien(services.start_task, get_store(), st.session_state["user"], id_viec)


def cb_nop(id_viec: str) -> None:
    tep = st.session_state.get(f"anh_{id_viec}")
    thuc_hien(
        services.submit_task, get_store(), get_notifier(), st.session_state["user"], id_viec,
        link=st.session_state.get(f"link_{id_viec}") or None,
        photo=tep.getvalue() if tep is not None else None,
        photo_name=tep.name if tep is not None else None,
        today=services.hom_nay(),
    )


def tab_viec_cua_toi(viec_cua_toi) -> None:
    if viec_cua_toi.empty:
        st.info("Bạn chưa có việc nào.")
        return
    for trang_thai in THU_TU_NHOM:
        nhom = viec_cua_toi[viec_cua_toi[config.COL_TRANG_THAI] == trang_thai]
        if nhom.empty:
            continue
        st.subheader(f"{trang_thai} ({len(nhom)})")
        for v in nhom.to_dict("records"):
            id_viec = v[config.COL_ID_VIEC]
            with st.container(border=True):
                the_viec(v)
                if trang_thai == config.TT_LAM_LAI and v[config.COL_GHI_CHU_QL]:
                    st.warning(f"Lý do trả lại: {v[config.COL_GHI_CHU_QL]}")
                if trang_thai == config.TT_HOAN_THANH:
                    st.caption(f"Đánh giá: {v[config.COL_SAO]} sao · Điểm: {v[config.COL_DIEM]}")
                if trang_thai in (config.TT_MOI_GIAO, config.TT_LAM_LAI):
                    st.button("Bắt đầu", key=f"start_{id_viec}", on_click=cb_bat_dau, args=(id_viec,))
                if trang_thai in (config.TT_DANG_LAM, config.TT_LAM_LAI):
                    with st.form(f"nop_form_{id_viec}"):
                        st.caption("Chứng minh hoàn thành: dán link HOẶC tải ảnh (chọn một).")
                        st.text_input("Link chứng minh (http:// hoặc https://)", key=f"link_{id_viec}")
                        st.file_uploader(
                            f"Ảnh chứng minh (JPG hoặc PNG, tối đa {config.ANH_MAX_BYTES // (1024 * 1024)} MB)",
                            type=["jpg", "jpeg", "png"], key=f"anh_{id_viec}")
                        st.form_submit_button("Báo cáo hoàn thành", key=f"nop_{id_viec}",
                                              on_click=cb_nop, args=(id_viec,))


def hien_kpi(nhan: str, diem, xong: int, tong: int) -> None:
    if diem is None:
        st.info("Chưa có việc trong quý này")
        return
    st.metric(nhan, f"{diem:.2f}%")
    st.caption(f"{xong}/{tong} việc đã hoàn thành")


def tab_kpi_cua_toi(viec_cua_toi, user: dict) -> None:
    quy = services.current_quarter(services.hom_nay())
    hien_kpi(f"KPI quý {quy}", *services.employee_kpi(viec_cua_toi, user[config.COL_ID_NV], quy))
    st.caption("Việc chưa đến hạn vẫn nằm trong mục tiêu quý, nên KPI tạm tính sẽ tăng dần khi việc được duyệt. "
               "100% tương ứng với mọi việc đúng hạn và đạt 4 sao; cao nhất là 120%.")


def man_hinh_nhan_vien(user: dict, viec_thay_duoc) -> None:
    tab_viec, tab_kpi = st.tabs(["Việc của tôi", "KPI của tôi"])
    with tab_viec:
        tab_viec_cua_toi(viec_thay_duoc)
    with tab_kpi:
        tab_kpi_cua_toi(viec_thay_duoc, user)


# --- Điểm vào ---

def main() -> None:
    try:
        get_store()
        nhan_su = load_employees()
    except db.SchemaError as e:
        st.error(f"File Google Sheet chưa đúng cấu trúc. {e}")
        st.stop()
    except db.StoreError:
        st.error(config.MSG_LOI_SHEET)
        st.stop()

    user = nguoi_dung_hien_tai(nhan_su)
    if user is None:
        hien_flash()
        man_hinh_dang_nhap()
        return

    with st.sidebar:
        st.markdown(f"**{user[config.COL_TEN]}**")
        st.caption("Quản lý" if user[config.COL_ROLE] == config.ROLE_QUAN_LY else "Nhân viên")
        st.button("Làm mới dữ liệu", key="refresh", on_click=cb_lam_moi)
        st.button("Đăng xuất", key="logout", on_click=cb_dang_xuat)

    hien_flash()
    try:
        # Lọc theo quyền trước khi dữ liệu được đưa ra giao diện
        viec_thay_duoc = services.visible_tasks(load_tasks(), user)
    except db.StoreError:
        st.error(config.MSG_LOI_SHEET)
        st.stop()

    if user[config.COL_ROLE] == config.ROLE_NHAN_VIEN:
        man_hinh_nhan_vien(user, viec_thay_duoc)
    else:
        st.info("Màn hình quản lý đang được xây dựng.")


main()
