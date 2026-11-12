"""Giao diện: lịch trình cá nhân trên lịch và đẩy việc sang Google Calendar."""
from datetime import date, time

import config as c
from tests.conftest import NHAN_SU, chu_tren_trang, dang_nhap, lich, mo_app, viec

# "Hôm nay" trong app_env là 2026-11-11
CUA_AN = lich(ID_Lich="L-1", Noi_Dung="Họp giao ban", Ngay="2026-11-16", Gio_Bat_Dau="08:30")
CUA_BINH = lich(ID_Lich="L-2", ID_NV="NV02", Noi_Dung="Việc riêng của Bình", Ngay="2026-11-16")
CUA_QL = lich(ID_Lich="L-3", ID_NV="QL01", Noi_Dung="Đi ngân hàng", Ngay="2026-11-17")


def nut_ca_nhan(at):
    return {b.key: b.label for b in at.button if (b.key or "").startswith("lcmuc_")}


def test_moi_nguoi_chi_thay_lich_ca_nhan_cua_minh(app_env):
    app_env(personal=[CUA_AN, CUA_BINH, CUA_QL], tasks=[viec(Han_Chot="2026-11-20")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception and nut_ca_nhan(at) == {"lcmuc_L-1_2026-11-16": "08:30 Họp giao ban"}
    assert "Việc riêng của Bình" not in chu_tren_trang(at) and "Đi ngân hàng" not in chu_tren_trang(at)
    at.button(key="logout").click().run()
    dang_nhap(at, "QL01", "1111")
    assert nut_ca_nhan(at) == {"lcmuc_L-3_2026-11-17": "Đi ngân hàng"}       # quản lý không thấy lịch riêng của nhân viên
    assert "Họp giao ban" not in chu_tren_trang(at) and "Việc riêng của Bình" not in chu_tren_trang(at)


def test_nhan_vien_chua_co_viec_van_thay_lich_va_o_them(app_env):
    app_env(personal=[CUA_AN])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception and len(nut_ca_nhan(at)) == 1 and at.button(key="lcf_them")


def test_them_muc_lap_hang_tuan_co_gio(app_env):
    store, _ = app_env()
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.text_input(key="lcf_noi_dung").set_value("Họp nhóm")
    at.date_input(key="lcf_ngay").set_value(date(2026, 11, 16))
    at.time_input(key="lcf_bat_dau").set_value(time(8, 30))
    at.time_input(key="lcf_ket_thuc").set_value(time(9, 0))
    at.selectbox(key="lcf_lap").set_value(c.LAP_TUAN)
    at.date_input(key="lcf_lap_den").set_value(date(2026, 11, 30))
    at.button(key="lcf_them").click().run()
    assert not at.exception and at.success[0].value == c.MSG_DA_LUU
    m = store.personal().iloc[0]
    assert (m[c.COL_ID_NV], m[c.COL_NOI_DUNG], m[c.COL_NGAY], m[c.COL_GIO_BAT_DAU], m[c.COL_GIO_KET_THUC], m[c.COL_LAP], m[c.COL_LAP_DEN]) == \
        ("NV01", "Họp nhóm", "2026-11-16", "08:30", "09:00", c.LAP_TUAN, "2026-11-30")
    assert sorted(nut_ca_nhan(at).values()) == ["08:30 Họp nhóm"] * 3          # 16, 23, 30 tháng 11
    e = app_env.calendar.events[0]
    assert e["calendar_id"] == "nv01@group.calendar.google.com" and e["lap"] == c.LAP_TUAN
    assert at.text_input(key="lcf_noi_dung").value == ""                       # ô nhập được xóa sau khi thêm


def test_them_muc_ca_ngay_mac_dinh_hom_nay(app_env):
    store, _ = app_env()
    at = dang_nhap(mo_app(), "QL01", "1111")
    at.text_input(key="lcf_noi_dung").set_value("Nộp tiền điện")
    at.button(key="lcf_them").click().run()
    m = store.personal().iloc[0]
    assert (m[c.COL_ID_NV], m[c.COL_NGAY], m[c.COL_GIO_BAT_DAU], m[c.COL_LAP]) == ("QL01", "2026-11-11", "", c.LAP_KHONG)
    assert nut_ca_nhan(at) == {f"lcmuc_{m[c.COL_ID_LICH]}_2026-11-11": "Nộp tiền điện"}


def test_them_sai_bao_loi_va_giu_o_nhap(app_env):
    store, _ = app_env()
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.text_input(key="lcf_noi_dung").set_value("Tập thể dục")
    at.selectbox(key="lcf_lap").set_value(c.LAP_NGAY)                          # lặp mà không chọn ngày kết thúc
    at.button(key="lcf_them").click().run()
    assert len(at.error) == 1 and "ngày kết thúc lặp" in at.error[0].value and len(store.personal()) == 0
    assert at.text_input(key="lcf_noi_dung").value == "Tập thể dục"


def test_google_loi_khi_them_thi_canh_bao_nhung_van_luu(app_env):
    store, _ = app_env()
    app_env.calendar.ok = False
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.text_input(key="lcf_noi_dung").set_value("Họp nhóm")
    at.button(key="lcf_them").click().run()
    assert at.warning[0].value == c.MSG_CHUA_DAY_LICH and len(at.success) == 0 and len(store.personal()) == 1


def test_nguoi_chua_cai_lich_google_them_binh_thuong(app_env):
    store, _ = app_env()
    at = dang_nhap(mo_app(), "NV02", "5678")
    at.text_input(key="lcf_noi_dung").set_value("Họp nhóm")
    at.button(key="lcf_them").click().run()
    assert at.success[0].value == c.MSG_DA_LUU and len(at.warning) == 0 and app_env.calendar.events == []


def test_bam_vao_muc_xem_chi_tiet_roi_danh_dau_xong(app_env):
    store, _ = app_env(personal=[lich(ID_Lich="L-1", Noi_Dung="Họp giao ban", Ngay="2026-11-09", Gio_Bat_Dau="08:30",
                                      Gio_Ket_Thuc="09:00", Lap=c.LAP_TUAN, Lap_Den="2026-11-30")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key="lcmuc_L-1_2026-11-16").click().run()
    chu = chu_tren_trang(at)
    assert not at.exception and "08:30" in chu and "09:00" in chu and c.LAP_TUAN in chu and "2026-11-30" in chu
    at.button(key="lcxong_L-1_2026-11-16").click().run()
    assert not at.exception and store.get_personal("L-1")[c.COL_DA_XONG] == "2026-11-16"
    nut = nut_ca_nhan(at)
    assert nut["lcmuc_L-1_2026-11-16"] == "~~08:30 Họp giao ban~~" and nut["lcmuc_L-1_2026-11-23"] == "08:30 Họp giao ban"
    at.button(key="lcmuc_L-1_2026-11-16").click().run()
    at.button(key="lcxong_L-1_2026-11-16").click().run()                       # bấm lần nữa để bỏ đánh dấu
    assert store.get_personal("L-1")[c.COL_DA_XONG] == ""


def test_xoa_muc_tu_hop_chi_tiet(app_env):
    store, _ = app_env(personal=[CUA_AN])
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key="lcmuc_L-1_2026-11-16").click().run()
    at.button(key="lcxoa_L-1_2026-11-16").click().run()
    assert not at.exception and len(store.personal()) == 0 and nut_ca_nhan(at) == {}
    assert len(app_env.calendar.deleted) == 1 and at.success[0].value == c.MSG_DA_LUU


def test_ngay_nhieu_muc_viec_duoc_giao_xep_truoc(app_env):
    app_env(tasks=[viec(ID_Viec=f"V-{i}", Ten_Viec=f"Việc {i}", Han_Chot="2026-11-16") for i in range(2)],
            personal=[lich(ID_Lich=f"L-{i}", Noi_Dung=f"Riêng {i}", Ngay="2026-11-16") for i in range(3)])
    at = dang_nhap(mo_app(), "NV01", "1234")
    hien = [b.label for b in at.button if (b.key or "").startswith(("lv_", "lcmuc_"))]
    assert hien == ["Việc 0", "Việc 1", "Riêng 0"]
    them = at.button(key="lvthem_2026-11-16")
    assert them.label == "+2 mục khác"
    them.click().run()
    chu = chu_tren_trang(at)
    assert not at.exception and all(x in chu for x in ["Việc 0", "Việc 1", "Riêng 0", "Riêng 1", "Riêng 2"])


def test_noi_dung_co_markdown_duoc_escape(app_env):
    app_env(personal=[lich(ID_Lich="L-1", Noi_Dung="[x](http://xau.vn) ~~a~~", Ngay="2026-11-16")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    nhan = nut_ca_nhan(at)["lcmuc_L-1_2026-11-16"]
    assert "[x](" not in nhan and "~~a~~" not in nhan


def test_o_ngay_gio_hong_tren_sheet_khong_lam_sap(app_env):
    app_env(personal=[lich(ID_Lich="L-1", Ngay="16/11/2026"), lich(ID_Lich="L-2", Gio_Bat_Dau="8h30"),
                      lich(ID_Lich="L-3", Lap="Lạ", Lap_Den="abc"), lich(ID_Lich="", Noi_Dung="thiếu mã")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception and "lcmuc_L-1_2026-11-16" not in nut_ca_nhan(at)
    at.button(key="lcmuc_L-2_2026-11-16").click().run()
    assert not at.exception


# --- Giao việc đẩy sang Google Calendar ---

def giao(at, nguoi="NV01"):
    at.text_input(key="gv_ten").set_value("Báo cáo tuần")
    at.selectbox(key="gv_nguoi_nhan").set_value(nguoi)
    at.date_input(key="gv_han_chot").set_value(date(2026, 11, 20))
    at.button(key="gv_submit").click().run()


def test_giao_viec_day_sang_google_calendar(app_env):
    app_env()
    at = dang_nhap(mo_app(), "QL01", "1111")
    giao(at)
    e = app_env.calendar.events[0]
    assert at.success[0].value == c.MSG_DA_LUU and len(app_env.calendar.events) == 1
    assert (e["calendar_id"], e["ngay"]) == ("nv01@group.calendar.google.com", date(2026, 11, 20)) and "Báo cáo tuần" in e["summary"]


def test_giao_viec_khi_google_loi_thi_canh_bao_va_van_luu(app_env):
    store, notifier = app_env()
    app_env.calendar.ok = False
    at = dang_nhap(mo_app(), "QL01", "1111")
    giao(at)
    assert [w.value for w in at.warning] == [c.MSG_CHUA_DAY_LICH] and len(at.success) == 0
    assert len(store.tasks()) == 1 and len(notifier.sent) == 1
