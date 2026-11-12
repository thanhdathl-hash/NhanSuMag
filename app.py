"""Giao diện Streamlit. Không ghi thẳng vào Sheet, không gửi Telegram: mọi thao tác đi qua services.py."""
import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import auth
import config
import db
import notifier
import services
import ui

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
    return notifier.from_secrets(st.secrets)


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
    except db.StoreError as e:
        flash("error", str(e))
        return False
    st.cache_data.clear()
    if not kq.kpi_saved:
        flash("warning", f"Đã duyệt, nhưng cột {config.COL_KPI_QUY} trên Sheet chưa cập nhật được.")
    if kq.warning:
        flash("warning", kq.warning)
    elif kq.notified:
        flash("success", config.MSG_DA_LUU)
    else:
        flash("warning", config.MSG_DA_LUU_CHUA_GUI)
    return True


# --- Đăng nhập ---

def cb_dang_nhap() -> None:
    try:
        nhan_su = load_employees()
    except db.StoreError as e:
        flash("error", str(e))
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


# --- Lịch hạn chót (dùng chung cho quản lý và nhân viên) ---

def _thang_dang_xem() -> tuple[int, int]:
    hom_nay = services.hom_nay()
    return st.session_state.setdefault("lich_thang", (hom_nay.year, hom_nay.month))


def cb_doi_thang(delta: int) -> None:
    st.session_state["lich_thang"] = services.shift_month(*_thang_dang_xem(), delta)


def cb_ve_thang_nay() -> None:
    st.session_state.pop("lich_thang", None)


def khoi_lich(tasks, ten_theo_id: dict | None = None) -> None:
    """Lịch tháng thể hiện hạn chót. Truyền ten_theo_id để ghi tên người nhận cạnh tên việc."""
    hom_nay = services.hom_nay()
    nam, thang = _thang_dang_xem()
    tieu_de, truoc, nay, sau = st.columns([6, 1, 1.4, 1], vertical_alignment="bottom")
    tieu_de.subheader(f"Lịch hạn chót · Tháng {thang}/{nam}")
    truoc.button("◀", key="lich_truoc", help="Tháng trước", on_click=cb_doi_thang, args=(-1,), width="stretch")
    nay.button("Hôm nay", key="lich_hom_nay", on_click=cb_ve_thang_nay, width="stretch")
    sau.button("▶", key="lich_sau", help="Tháng sau", on_click=cb_doi_thang, args=(1,), width="stretch")
    st.html(ui.calendar_html(nam, thang, services.calendar_events(tasks, nam, thang, hom_nay), hom_nay, ten_theo_id))
    st.html(ui.legend_html())


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
    khoi_lich(viec_cua_toi)
    for trang_thai in THU_TU_NHOM:
        nhom = viec_cua_toi[viec_cua_toi[config.COL_TRANG_THAI] == trang_thai]
        if nhom.empty:
            continue
        st.subheader(f"{trang_thai} ({len(nhom)})")
        for v in nhom.to_dict("records"):
            id_viec = v[config.COL_ID_VIEC]
            with st.container(border=True, key=f"khoi_viec_{id_viec}"):
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
    st.html(ui.stat_cards_html(services.dashboard_counts(viec_thay_duoc, services.hom_nay())))
    tab_viec, tab_kpi = st.tabs(["Việc của tôi", "KPI của tôi"])
    with tab_viec:
        tab_viec_cua_toi(viec_thay_duoc)
    with tab_kpi:
        tab_kpi_cua_toi(viec_thay_duoc, user)


# --- Màn hình Quản lý ---

GO_TAY = ""          # lựa chọn "không dùng mẫu" trong ô chọn mẫu
TAT_CA = "Tất cả"
TRONG_SO_MAC_DINH = 3
_LINK_AN_TOAN = re.compile(r"https?://[^\s<>]+")


def ten_theo_id(nhan_su) -> dict:
    return dict(zip(nhan_su[config.COL_ID_NV], nhan_su[config.COL_TEN]))


def cb_chon_mau() -> None:
    """Chọn mẫu thì tự điền tên, mô tả, trọng số. Trọng số được chép sang việc, sửa mẫu sau không đổi việc cũ."""
    id_mau = st.session_state.get("gv_mau")
    if not id_mau:
        return
    try:
        mau = load_templates()
    except db.StoreError as e:
        flash("error", str(e))
        return
    khop = mau[mau[config.COL_ID_MAU] == id_mau]
    if khop.empty:
        return
    m = khop.iloc[0]
    st.session_state["gv_ten"] = m[config.COL_TEN_VIEC]
    st.session_state["gv_mo_ta"] = m[config.COL_MO_TA]
    try:
        trong_so = int(m[config.COL_TRONG_SO_DIEM])
    except ValueError:
        trong_so = TRONG_SO_MAC_DINH
    st.session_state["gv_trong_so"] = min(config.TRONG_SO_MAX, max(config.TRONG_SO_MIN, trong_so))


def cb_giao_viec() -> None:
    da_luu = thuc_hien(
        services.create_task, get_store(), get_notifier(), st.session_state["user"],
        ten_viec=st.session_state.get("gv_ten", ""),
        mo_ta=st.session_state.get("gv_mo_ta", ""),
        nguoi_nhan=st.session_state.get("gv_nguoi_nhan") or "",
        han_chot=st.session_state.get("gv_han_chot"),
        trong_so=int(st.session_state.get("gv_trong_so", TRONG_SO_MAC_DINH)),
        today=services.hom_nay(),
    )
    if da_luu:   # xóa ô nhập để giao việc tiếp; khi lỗi thì giữ nguyên
        st.session_state["gv_mau"] = GO_TAY
        st.session_state["gv_ten"] = ""
        st.session_state["gv_mo_ta"] = ""
        st.session_state["gv_trong_so"] = TRONG_SO_MAC_DINH


def tab_giao_viec(nhan_su) -> None:
    try:
        mau = load_templates()
    except db.StoreError as e:
        st.error(str(e))
        return
    ten_mau = dict(zip(mau[config.COL_ID_MAU], mau[config.COL_TEN_VIEC]))
    st.selectbox("Chọn từ thư viện mẫu", [GO_TAY, *ten_mau], key="gv_mau", on_change=cb_chon_mau,
                 format_func=lambda i: "(Gõ tay)" if i == GO_TAY else ten_mau[i])
    st.text_input("Tên việc", key="gv_ten")
    st.text_area("Mô tả", key="gv_mo_ta")
    # Giá trị mặc định truyền qua `value` để trình duyệt nhận ngay từ lần vẽ đầu;
    # nếu chỉ đặt qua session_state, người bấm nhanh có thể gửi đi giá trị nhỏ nhất (1).
    st.number_input("Trọng số (1 đến 5)", min_value=config.TRONG_SO_MIN, max_value=config.TRONG_SO_MAX,
                    value=TRONG_SO_MAC_DINH, step=1, key="gv_trong_so")
    nhan_vien = nhan_su[nhan_su[config.COL_ROLE] == config.ROLE_NHAN_VIEN]
    ten = ten_theo_id(nhan_vien)
    st.selectbox("Người nhận", list(ten), index=None, placeholder="Chọn nhân viên", key="gv_nguoi_nhan",
                 format_func=lambda i: f"{ten[i]} ({i})")
    st.date_input("Hạn chót", value=services.hom_nay(), format="DD/MM/YYYY", key="gv_han_chot")
    st.button("Giao việc", key="gv_submit", type="primary", on_click=cb_giao_viec)


@st.cache_data(ttl=600, max_entries=50, show_spinner=False)
def _tai_anh(file_id: str) -> bytes:
    """Tải ảnh ở phía máy chủ. Trình duyệt chỉ nhận dữ liệu ảnh, không nhận URL chứa token."""
    du_lieu = get_notifier().fetch_photo(file_id)
    if du_lieu is None:
        raise LookupError(file_id)     # không cache kết quả thất bại
    return du_lieu


def hien_chung_minh(gia_tri: str) -> None:
    if gia_tri.startswith(config.TG_PREFIX):
        try:
            st.image(_tai_anh(gia_tri[len(config.TG_PREFIX):]), width=480)
        except LookupError:
            st.warning("Chưa tải được ảnh chứng minh từ Telegram. "
                       "Ảnh vẫn nằm trong cuộc trò chuyện của bạn với bot.")
        except Exception:   # dữ liệu tải về không phải ảnh hợp lệ
            st.warning("Không hiển thị được ảnh chứng minh. Hãy xem ảnh trong cuộc trò chuyện với bot.")
    elif _LINK_AN_TOAN.fullmatch(gia_tri):
        st.markdown(f"[Mở link chứng minh](<{gia_tri}>)")
    elif gia_tri:
        st.code(gia_tri)     # không phải link hợp lệ: chỉ hiện dạng chữ
    else:
        st.caption("(Không có chứng minh)")


def cb_duyet(id_viec: str) -> None:
    thuc_hien(services.approve_task, get_store(), get_notifier(), st.session_state["user"], id_viec,
              stars=st.session_state.get(f"sao_{id_viec}"), today=services.hom_nay())


def cb_tra_lai(id_viec: str) -> None:
    thuc_hien(services.return_task, get_store(), get_notifier(), st.session_state["user"], id_viec,
              ly_do=st.session_state.get(f"ly_do_{id_viec}", ""))


def tab_cho_duyet(tasks, nhan_su) -> None:
    cho = tasks[tasks[config.COL_TRANG_THAI] == config.TT_CHO_DUYET]
    if cho.empty:
        st.info("Không có việc nào đang chờ duyệt.")
        return
    ten = ten_theo_id(nhan_su)
    for v in cho.to_dict("records"):
        id_viec = v[config.COL_ID_VIEC]
        with st.container(border=True, key=f"khoi_duyet_{id_viec}"):
            the_viec(v)
            st.caption(f"Người làm: {ten.get(v[config.COL_NGUOI_NHAN], v[config.COL_NGUOI_NHAN])} · "
                       f"Báo cáo ngày: {v[config.COL_NGAY_HOAN_THANH]}")
            hien_chung_minh(v[config.COL_LINK])
            cot_duyet, cot_tra = st.columns(2)
            with cot_duyet:
                st.radio("Chấm sao", list(range(1, 6)), index=None, horizontal=True, key=f"sao_{id_viec}",
                         format_func=lambda n: f"{n} ⭐")
                st.button("Duyệt", key=f"duyet_{id_viec}", type="primary", on_click=cb_duyet, args=(id_viec,))
            with cot_tra:
                st.text_input("Lý do trả lại", key=f"ly_do_{id_viec}")
                st.button("Trả lại", key=f"tra_{id_viec}", on_click=cb_tra_lai, args=(id_viec,))


def tab_tong_quan(tasks, nhan_su) -> None:
    hom_nay = services.hom_nay()
    ds_quy = services.quarters(tasks, hom_nay)
    quy = st.selectbox("Quý", ds_quy, index=ds_quy.index(services.current_quarter(hom_nay)), key="tq_quy")
    trong_quy = tasks[tasks[config.COL_QUY] == quy]

    st.html(ui.stat_cards_html(services.dashboard_counts(trong_quy, hom_nay)))

    trai, phai = st.columns(2)
    with trai.container(border=True, key="khoi_ti_le"):
        st.markdown(f"**Tỉ lệ công việc quý {quy}**")
        if trong_quy.empty:
            st.caption("Chưa có việc trong quý này.")
        else:
            st.altair_chart(ui.status_donut(services.status_counts(trong_quy)), width="stretch")
    with phai.container(border=True, key="khoi_theo_nhan_vien"):
        st.markdown("**Công việc theo nhân viên**")
        if trong_quy.empty:
            st.caption("Chưa có việc trong quý này.")
        else:
            st.altair_chart(ui.workload_bars(services.workload_table(trong_quy, nhan_su, hom_nay)), width="stretch")

    khoi_lich(tasks, ten_theo_id(nhan_su))

    st.subheader(f"KPI quý {quy}")
    bang = services.kpi_table(tasks, nhan_su, quy)
    hien_thi = bang[[config.COL_TEN]].rename(columns={config.COL_TEN: "Nhân viên"})
    hien_thi["KPI"] = [("Chưa có việc" if d is None else f"{d:.2f}%") for d in bang[config.KQ_KPI]]
    hien_thi["Việc đã hoàn thành"] = [f"{x}/{t}" for x, t in zip(bang[config.KQ_HOAN_THANH], bang[config.KQ_TONG_VIEC])]
    st.dataframe(hien_thi, hide_index=True, width="stretch")
    st.caption("Việc chưa đến hạn vẫn nằm trong mục tiêu quý, nên KPI giữa quý thấp và tăng dần khi việc được duyệt.")
    co_kpi = bang[bang[config.KQ_KPI].notna()]
    if not co_kpi.empty:
        st.bar_chart(co_kpi.set_index(config.COL_TEN)[config.KQ_KPI].astype(float), x_label="KPI (%)",
                     horizontal=True, color="#5b5fe9", height=60 + 36 * len(co_kpi))

    st.subheader("Việc quá hạn chưa nộp")
    qua_han = services.overdue_tasks(tasks, hom_nay)
    if qua_han.empty:
        st.info("Không có việc quá hạn.")
    else:
        ten = ten_theo_id(nhan_su)
        st.dataframe(pd.DataFrame({
            "Việc": qua_han[config.COL_TEN_VIEC],
            "Người nhận": [ten.get(i, i) for i in qua_han[config.COL_NGUOI_NHAN]],
            "Hạn chót": qua_han[config.COL_HAN_CHOT],
            "Trạng thái": qua_han[config.COL_TRANG_THAI],
        }), hide_index=True, width="stretch")


def tab_tat_ca(tasks, nhan_su) -> None:
    ten = ten_theo_id(nhan_su)
    c1, c2, c3 = st.columns(3)
    nv = c1.selectbox("Nhân viên", [TAT_CA, *ten], key="all_nv",
                      format_func=lambda i: i if i == TAT_CA else f"{ten[i]} ({i})")
    tt = c2.selectbox("Trạng thái", [TAT_CA, *config.TRANG_THAI], key="all_tt")
    quy = c3.selectbox("Quý", [TAT_CA, *services.quarters(tasks, services.hom_nay())], key="all_quy")
    loc = tasks
    if nv != TAT_CA:
        loc = loc[loc[config.COL_NGUOI_NHAN] == nv]
    if tt != TAT_CA:
        loc = loc[loc[config.COL_TRANG_THAI] == tt]
    if quy != TAT_CA:
        loc = loc[loc[config.COL_QUY] == quy]
    st.caption(f"{len(loc)} việc")
    st.dataframe(loc, hide_index=True, width="stretch")


def man_hinh_quan_ly(tasks, nhan_su) -> None:
    t1, t2, t3, t4 = st.tabs(["Tổng quan", "Giao việc", config.TT_CHO_DUYET, "Tất cả công việc"])
    with t1:
        tab_tong_quan(tasks, nhan_su)
    with t2:
        tab_giao_viec(nhan_su)
    with t3:
        tab_cho_duyet(tasks, nhan_su)
    with t4:
        tab_tat_ca(tasks, nhan_su)


# --- Điểm vào ---

def main() -> None:
    try:
        get_store()
        nhan_su = load_employees()
    except db.SchemaError as e:
        st.error(f"File Google Sheet chưa đúng cấu trúc. {e}")
        st.stop()
    except db.StoreError as e:
        st.error(str(e))
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

    st.html(ui.CSS)
    hien_flash()
    try:
        viec_tho = load_tasks()
    except db.StoreError as e:
        st.error(str(e))
        st.stop()
    # Lọc theo quyền trước khi dữ liệu được đưa ra giao diện
    viec_thay_duoc = services.visible_tasks(services.prepare_tasks(viec_tho), user)
    if user[config.COL_ROLE] == config.ROLE_QUAN_LY:
        for canh_bao in services.sheet_warnings(viec_tho, nhan_su):
            st.warning(canh_bao)

    if user[config.COL_ROLE] == config.ROLE_NHAN_VIEN:
        man_hinh_nhan_vien(user, viec_thay_duoc)
    elif user[config.COL_ROLE] == config.ROLE_QUAN_LY:
        man_hinh_quan_ly(viec_thay_duoc, nhan_su)
    else:
        st.error(f"Tài khoản chưa được gán vai trò hợp lệ ở cột {config.COL_ROLE}. Hãy báo quản lý.")


main()
