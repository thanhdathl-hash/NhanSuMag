"""Giao diện Streamlit. Không ghi thẳng vào Sheet, không gửi Telegram: mọi thao tác đi qua services.py."""
import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import auth
import config
import db
import gcal
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
def get_calendar():
    return gcal.from_secrets(st.secrets)


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


@st.cache_data(ttl=config.CACHE_TTL_GIAY)
def load_personal():
    return get_store().personal()


# --- Thông báo sau thao tác ---

def flash(kieu: str, noi_dung: str) -> None:
    st.session_state.setdefault("flash", []).append((kieu, noi_dung))


def hien_flash() -> None:
    # Luôn đặt trong một khung cố định: thông báo hiện rồi mất không làm xê dịch các khối bên dưới
    # (nếu xê dịch, ô "Thêm lịch trình cá nhân" đang mở sẽ tự gập lại giữa lúc người dùng gõ).
    with st.container():
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
    tron_ven = True
    if kq.warning:
        flash("warning", kq.warning)
        tron_ven = False
    elif not kq.notified:
        flash("warning", config.MSG_DA_LUU_CHUA_GUI)
        tron_ven = False
    if kq.calendar_pushed is False:
        flash("warning", config.MSG_CHUA_DAY_LICH)
        tron_ven = False
    if tron_ven:
        flash("success", config.MSG_DA_LUU)
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


def chi_tiet_viec(v: dict, ten_theo_id: dict | None) -> None:
    """Toàn bộ thông tin của một việc, chỉ để xem."""
    st.markdown(f"**{ui.md_escape(v[config.COL_TEN_VIEC])}**")
    dong = []
    if ten_theo_id is not None:
        nguoi = ten_theo_id.get(v[config.COL_NGUOI_NHAN], v[config.COL_NGUOI_NHAN])
        dong.append(f"Người nhận: {ui.md_escape(nguoi)}")
    nhom = services.task_group(v[config.COL_TRANG_THAI], v[config.COL_HAN_CHOT], services.hom_nay())
    qua_han = " (đã quá hạn)" if nhom == config.NHOM_QUA_HAN else ""
    dong.append(f"Trạng thái: {ui.md_escape(v[config.COL_TRANG_THAI])}{qua_han}")
    dong.append(f"Hạn chót: {ui.md_escape(v[config.COL_HAN_CHOT])} · Ngày giao: {ui.md_escape(v[config.COL_NGAY_GIAO])} "
                f"· Trọng số: {ui.md_escape(v[config.COL_TRONG_SO])}")
    if v[config.COL_NGAY_HOAN_THANH]:
        dong.append(f"Báo cáo ngày: {ui.md_escape(v[config.COL_NGAY_HOAN_THANH])}")
    if v[config.COL_SAO]:
        dong.append(f"Đánh giá: {ui.md_escape(v[config.COL_SAO])} sao · Điểm: {ui.md_escape(v[config.COL_DIEM])}")
    st.markdown("  \n".join(dong))
    if v[config.COL_MO_TA]:
        st.markdown(f"Mô tả: {ui.md_escape(v[config.COL_MO_TA])}")
    if v[config.COL_GHI_CHU_QL]:
        st.warning(f"Lý do trả lại: {v[config.COL_GHI_CHU_QL]}")
    if v[config.COL_LINK]:
        hien_chung_minh(v[config.COL_LINK])
    st.caption(f"Mã việc: {v[config.COL_ID_VIEC]}")


def _nhan_lich(m: dict) -> str:
    """Nhãn một mục lịch cá nhân: giờ đứng trước nội dung, gạch ngang nếu đã xong."""
    gio = m[config.COL_GIO_BAT_DAU]
    nhan = (f"{ui.md_escape(gio)} " if gio else "") + ui.md_escape(m[config.COL_NOI_DUNG])
    return f"~~{nhan}~~" if m["xong"] else nhan


def cb_lich_xong(id_lich: str, ngay, da_xong: bool) -> None:
    thuc_hien(services.set_personal_done, get_store(), st.session_state["user"], id_lich, ngay, da_xong)
    st.session_state["dong_hop"] = True     # báo hộp chi tiết tự đóng để trang hiện kết quả


def cb_lich_xoa(id_lich: str) -> None:
    thuc_hien(services.delete_personal, get_store(), get_calendar(), st.session_state["user"], id_lich)
    st.session_state["dong_hop"] = True


def chi_tiet_lich(m: dict) -> None:
    """Một lần xảy ra của mục lịch cá nhân, kèm nút đánh dấu xong và xóa."""
    id_lich, ngay = m[config.COL_ID_LICH], m["ngay_xay_ra"]
    st.markdown(f"**{ui.md_escape(m[config.COL_NOI_DUNG])}**")
    gio = "Cả ngày"
    if m[config.COL_GIO_BAT_DAU]:
        gio = m[config.COL_GIO_BAT_DAU] + (f" đến {m[config.COL_GIO_KET_THUC]}" if m[config.COL_GIO_KET_THUC] else "")
    co_lap = m[config.COL_LAP] in (config.LAP_NGAY, config.LAP_TUAN)
    dong = ["Lịch cá nhân (chỉ mình bạn thấy trong app)", f"Ngày: {ngay.isoformat()} · Giờ: {ui.md_escape(gio)}"]
    if co_lap:
        dong.append(f"Lặp lại: {ui.md_escape(m[config.COL_LAP])}, đến {ui.md_escape(m[config.COL_LAP_DEN])}")
    dong.append("Trạng thái: " + ("đã xong" if m["xong"] else "chưa xong"))
    st.markdown("  \n".join(dong))
    khoa = f"{id_lich}_{ngay.isoformat()}"
    xong, xoa = st.columns(2)
    xong.button("Bỏ đánh dấu xong" if m["xong"] else "Đánh dấu xong", key=f"lcxong_{khoa}", width="stretch",
                on_click=cb_lich_xong, args=(id_lich, ngay, not m["xong"]))
    xoa.button("Xóa cả chuỗi lặp" if co_lap else "Xóa", key=f"lcxoa_{khoa}", width="stretch",
               on_click=cb_lich_xoa, args=(id_lich,))


@st.dialog("Chi tiết", width="large")
def hop_chi_tiet(ds_muc: list[tuple[str, dict]], ten_theo_id: dict | None) -> None:
    """ds_muc: danh sách ("viec", dòng việc) hoặc ("lich", lần xảy ra của mục lịch cá nhân)."""
    if st.session_state.pop("dong_hop", False):
        st.rerun()      # một nút trong hộp vừa chạy xong: tải lại cả trang, hộp đóng
    for i, (loai, muc) in enumerate(ds_muc):
        if i:
            st.divider()
        if loai == "viec":
            chi_tiet_viec(muc, ten_theo_id)
        else:
            chi_tiet_lich(muc)


def khoi_lich(tasks, lich_cua_toi, ten_theo_id: dict | None = None) -> None:
    """Lịch tháng: hạn chót các việc và lịch trình cá nhân của người đang đăng nhập. Bấm vào một mục để xem chi tiết.

    Truyền ten_theo_id để ghi tên người nhận cạnh tên việc.
    """
    hom_nay = services.hom_nay()
    nam, thang = _thang_dang_xem()
    tieu_de, truoc, nay, sau = st.columns([6, 1, 1.4, 1], vertical_alignment="bottom")
    tieu_de.subheader(f"Lịch làm việc · Tháng {thang}/{nam}")
    truoc.button("◀", key="lich_truoc", help="Tháng trước", on_click=cb_doi_thang, args=(-1,), width="stretch")
    nay.button("Hôm nay", key="lich_hom_nay", on_click=cb_ve_thang_nay, width="stretch")
    sau.button("▶", key="lich_sau", help="Tháng sau", on_click=cb_doi_thang, args=(1,), width="stretch")

    lich_viec = services.calendar_events(tasks, nam, thang, hom_nay)
    lich_rieng = services.personal_events(lich_cua_toi, nam, thang)
    can_xem = None
    with st.container(key="luoi_lich"):
        for cot, thu in zip(st.columns(7), ui.THU):
            cot.html(f'<div class="gv-thu">{thu}</div>')
        for tuan in ui.month_weeks(nam, thang):
            for cot, ngay in zip(st.columns(7), tuan):
                trong_thang = ngay.month == thang
                loai = "lichngoai" if not trong_thang else ("lichnay" if ngay == hom_nay else "lichngay")
                with cot.container(key=f"{loai}_{ngay.isoformat()}"):
                    st.html(f'<span class="gv-so-ngay">{ngay.day}</span>')
                    if not trong_thang:
                        continue
                    # việc được giao xếp trước, rồi tới lịch cá nhân theo giờ
                    ds = [("viec", v) for v in lich_viec.get(ngay, [])] + [("lich", m) for m in lich_rieng.get(ngay, [])]
                    for kieu, muc in ds[:ui.SO_VIEC_MOI_O]:
                        if kieu == "viec":
                            nhan = ui.md_escape(muc[config.COL_TEN_VIEC])
                            if ten_theo_id is not None:
                                nguoi = ten_theo_id.get(muc[config.COL_NGUOI_NHAN], muc[config.COL_NGUOI_NHAN])
                                nhan += f" · {ui.md_escape(nguoi)}"
                            khoa = f"lv_{muc['nhom']}_{muc[config.COL_ID_VIEC]}"
                        else:
                            nhan = _nhan_lich(muc)
                            khoa = f"lcmuc_{muc[config.COL_ID_LICH]}_{ngay.isoformat()}"
                        if st.button(nhan, key=khoa, width="stretch"):
                            can_xem = [(kieu, muc)]
                    if len(ds) > ui.SO_VIEC_MOI_O:
                        if st.button(f"+{len(ds) - ui.SO_VIEC_MOI_O} mục khác",
                                     key=f"lvthem_{ngay.isoformat()}", width="stretch"):
                            can_xem = ds
    st.html(ui.legend_html())
    st.caption("Bấm vào một mục trên lịch để xem chi tiết.")
    khoi_them_lich()
    if can_xem:
        hop_chi_tiet(can_xem, ten_theo_id)


def cb_them_lich() -> None:
    da_luu = thuc_hien(
        services.add_personal, get_store(), get_calendar(), st.session_state["user"],
        noi_dung=st.session_state.get("lcf_noi_dung", ""),
        ngay=st.session_state.get("lcf_ngay"),
        gio_bat_dau=st.session_state.get("lcf_bat_dau"),
        gio_ket_thuc=st.session_state.get("lcf_ket_thuc"),
        lap=st.session_state.get("lcf_lap", config.LAP_KHONG),
        lap_den=st.session_state.get("lcf_lap_den"),
    )
    if da_luu:   # xóa ô nhập để thêm mục tiếp; khi lỗi thì giữ nguyên
        st.session_state["lcf_noi_dung"] = ""
        st.session_state["lcf_bat_dau"] = None
        st.session_state["lcf_ket_thuc"] = None
        st.session_state["lcf_lap"] = config.LAP_KHONG
        st.session_state["lcf_lap_den"] = None


def khoi_them_lich() -> None:
    """Ô thêm lịch trình cá nhân: việc nhỏ, sinh hoạt hằng ngày, ngoài việc được giao."""
    with st.expander("➕ Thêm lịch trình cá nhân"):
        st.caption("Dành cho việc ngoài việc được giao. Trong app chỉ mình bạn thấy. "
                   "Nếu bạn đã cài lịch Google, mục này cũng được đẩy sang đó.")
        st.text_input("Nội dung", key="lcf_noi_dung", max_chars=config.NOI_DUNG_TOI_DA)
        c1, c2, c3 = st.columns(3)
        c1.date_input("Ngày", value=services.hom_nay(), format="DD/MM/YYYY", key="lcf_ngay")
        c2.time_input("Giờ bắt đầu (bỏ trống nếu cả ngày)", value=None, step=900, key="lcf_bat_dau")
        c3.time_input("Giờ kết thúc (có thể bỏ trống)", value=None, step=900, key="lcf_ket_thuc")
        c4, c5 = st.columns(2)
        c4.selectbox("Lặp lại", config.LAP_KIEU, key="lcf_lap")
        c5.date_input("Lặp đến hết ngày (khi có lặp)", value=None, format="DD/MM/YYYY", key="lcf_lap_den")
        st.button("Thêm vào lịch", key="lcf_them", on_click=cb_them_lich)


# --- Khối "Việc cần xử lý" ---

def khoi_can_xu_ly(viec_thay_duoc, user: dict, ten_theo_id: dict | None = None) -> None:
    """Những việc cần để ý ngay, tính từ dữ liệu hiện có. Kèm một dòng nhắc ở thanh bên."""
    ds_nhom = services.todo_groups(viec_thay_duoc, user, services.hom_nay())
    so = services.todo_count(ds_nhom)
    if so == 0:
        st.caption("✅ Không có việc nào cần xử lý.")
        return
    st.sidebar.markdown(f"🔔 **{so} việc cần xử lý**")
    with st.container(key="khoi_can_xu_ly"):
        with st.expander(f"🔔 Việc cần xử lý ({so})", expanded=True):
            for nhom in ds_nhom:
                dong = [f"**{nhom['nhan']}** ({len(nhom['viec'])})", ""]
                for v in nhom["viec"]:
                    muc = [ui.md_escape(v[config.COL_TEN_VIEC])]
                    if ten_theo_id is not None:
                        muc.append(ui.md_escape(ten_theo_id.get(v[config.COL_NGUOI_NHAN], v[config.COL_NGUOI_NHAN])))
                    muc.append(f"hạn {ui.md_escape(v[config.COL_HAN_CHOT])}")
                    if v[config.COL_TRANG_THAI] == config.TT_LAM_LAI and v[config.COL_GHI_CHU_QL]:
                        muc.append(f"lý do trả lại: {ui.md_escape(v[config.COL_GHI_CHU_QL])}")
                    dong.append("- " + " · ".join(muc))
                st.markdown("\n".join(dong))


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


def tab_viec_cua_toi(viec_cua_toi, lich_cua_toi) -> None:
    khoi_lich(viec_cua_toi, lich_cua_toi)
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


def man_hinh_nhan_vien(user: dict, viec_thay_duoc, lich_cua_toi) -> None:
    st.html(ui.stat_cards_html(services.dashboard_counts(viec_thay_duoc, services.hom_nay())))
    khoi_can_xu_ly(viec_thay_duoc, user)
    tab_viec, tab_kpi = st.tabs(["Việc của tôi", "KPI của tôi"])
    with tab_viec:
        tab_viec_cua_toi(viec_thay_duoc, lich_cua_toi)
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
        calendar=get_calendar(),
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


def tab_tong_quan(tasks, nhan_su, lich_cua_toi) -> None:
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

    khoi_lich(tasks, lich_cua_toi, ten_theo_id(nhan_su))

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


def man_hinh_quan_ly(user: dict, tasks, nhan_su, lich_cua_toi) -> None:
    khoi_can_xu_ly(tasks, user, ten_theo_id(nhan_su))
    t1, t2, t3, t4 = st.tabs(["Tổng quan", "Giao việc", config.TT_CHO_DUYET, "Tất cả công việc"])
    with t1:
        tab_tong_quan(tasks, nhan_su, lich_cua_toi)
    with t2:
        tab_giao_viec(nhan_su)
    with t3:
        tab_cho_duyet(tasks, nhan_su)
    with t4:
        tab_tat_ca(tasks, nhan_su)


# --- Điểm vào ---

def main() -> None:
    st.session_state.pop("dong_hop", None)
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
        lich_tho = load_personal()
    except db.StoreError as e:
        st.error(str(e))
        st.stop()
    # Lọc theo quyền trước khi dữ liệu được đưa ra giao diện
    viec_thay_duoc = services.visible_tasks(services.prepare_tasks(viec_tho), user)
    if user[config.COL_ROLE] == config.ROLE_QUAN_LY:
        for canh_bao in services.sheet_warnings(viec_tho, nhan_su):
            st.warning(canh_bao)

    lich_cua_toi = services.visible_personal(lich_tho, user)   # lịch cá nhân: chỉ của người đang đăng nhập

    if user[config.COL_ROLE] == config.ROLE_NHAN_VIEN:
        man_hinh_nhan_vien(user, viec_thay_duoc, lich_cua_toi)
    elif user[config.COL_ROLE] == config.ROLE_QUAN_LY:
        man_hinh_quan_ly(user, viec_thay_duoc, nhan_su, lich_cua_toi)
    else:
        st.error(f"Tài khoản chưa được gán vai trò hợp lệ ở cột {config.COL_ROLE}. Hãy báo quản lý.")


main()
