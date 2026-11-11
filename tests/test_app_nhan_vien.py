import requests

import config as c
import db
from tests.conftest import NHAN_SU, chu_tren_trang, dang_nhap, mo_app, viec, viec_vi_du_spec
from tests.fakes import FakeSpreadsheet, FakeWorksheet

ID = "V-00000001"
HAI_VIEC = [viec(), viec(ID_Viec="V-00000002", Ten_Viec="Việc B", Nguoi_Nhan="NV02")]


def test_chua_dang_nhap_chi_thay_form(app_env):
    app_env(tasks=HAI_VIEC)
    at = mo_app()
    assert not at.exception
    assert at.text_input(key="login_id") and len(at.tabs) == 0
    assert "Việc A" not in chu_tren_trang(at)


def test_sai_pin_bao_loi_chung(app_env):
    app_env()
    at = dang_nhap(mo_app(), "NV01", "0000")
    assert at.error[0].value == c.MSG_DANG_NHAP_SAI and "user" not in at.session_state


def test_khoa_sau_5_lan_sai(app_env):
    app_env()
    at = mo_app()
    for _ in range(5):
        dang_nhap(at, "NV01", "0000")
    dang_nhap(at, "NV01", "1234")
    assert at.error[0].value == c.MSG_TAI_KHOAN_KHOA and "user" not in at.session_state


def test_nhan_vien_chi_thay_viec_cua_minh(app_env):
    app_env(tasks=HAI_VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception
    noi_dung = chu_tren_trang(at)
    assert "Việc A" in noi_dung and "Việc B" not in noi_dung
    assert [t.label for t in at.tabs] == ["Việc của tôi", "KPI của tôi"]


def test_bat_dau_roi_bao_cao_bang_link(app_env):
    store, notifier = app_env(tasks=HAI_VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key=f"start_{ID}").click().run()
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM
    at.text_input(key=f"link_{ID}").set_value("https://a.vn")
    at.button(key=f"nop_{ID}").click().run()
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_NGAY_HOAN_THANH]) == (c.TT_CHO_DUYET, "2026-11-11")
    assert at.success[0].value == c.MSG_DA_LUU and not at.exception
    assert notifier.sent[0][0] == "100"


def test_bao_cao_thieu_chung_minh_bao_loi(app_env):
    store, _ = app_env(tasks=[viec(Trang_Thai=c.TT_DANG_LAM)])
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key=f"nop_{ID}").click().run()
    assert len(at.error) == 1 and "chứng minh" in at.error[0].value
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM


def test_link_sai_bao_loi_va_giu_o_nhap(app_env):
    store, _ = app_env(tasks=[viec(Trang_Thai=c.TT_DANG_LAM)])
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.text_input(key=f"link_{ID}").set_value("drive.google.com/x")
    at.button(key=f"nop_{ID}").click().run()
    assert len(at.error) == 1 and at.text_input(key=f"link_{ID}").value == "drive.google.com/x"
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM


def test_telegram_loi_hien_canh_bao(app_env):
    store, notifier = app_env(tasks=[viec(Trang_Thai=c.TT_DANG_LAM)])
    notifier.ok = False
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.text_input(key=f"link_{ID}").set_value("https://a.vn")
    at.button(key=f"nop_{ID}").click().run()
    assert at.warning[0].value == c.MSG_DA_LUU_CHUA_GUI
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_viec_lam_lai_hien_ly_do_va_ca_hai_nut(app_env):
    app_env(tasks=[viec(Trang_Thai=c.TT_LAM_LAI, Ghi_Chu_QL="Thiếu số liệu")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert "Thiếu số liệu" in chu_tren_trang(at)
    assert at.button(key=f"start_{ID}") and at.button(key=f"nop_{ID}")


def test_viec_cho_duyet_khong_co_nut(app_env):
    app_env(tasks=[viec(Trang_Thai=c.TT_CHO_DUYET)])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert [b.key for b in at.button if b.key and b.key.startswith(("start_", "nop_"))] == []


def test_kpi_cua_toi(app_env):
    app_env(tasks=viec_vi_du_spec(da_duyet=True))
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert at.metric[0].value == "49.57%"
    assert "3/4 việc đã hoàn thành" in chu_tren_trang(at)


def test_kpi_chua_co_viec(app_env):
    app_env(tasks=viec_vi_du_spec(da_duyet=True))
    at = dang_nhap(mo_app(), "NV02", "5678")
    assert "Chưa có việc trong quý này" in chu_tren_trang(at) and len(at.metric) == 0


def test_mat_ket_noi_sheet_hien_thong_bao(app_env):
    store, _ = app_env(tasks=HAI_VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    store._spreadsheet.worksheet(c.SHEET_VIEC).fail_with = requests.ConnectionError("x")
    at.button(key=f"start_{ID}").click().run()
    assert not at.exception and c.MSG_LOI_SHEET in chu_tren_trang(at)
    assert "user" in at.session_state                      # không bị đăng xuất


def test_mat_ket_noi_luc_mo_app(app_env):
    store, _ = app_env()
    store._spreadsheet.worksheet(c.SHEET_NHAN_SU).fail_with = requests.ConnectionError("x")
    at = mo_app()
    assert not at.exception and at.error[0].value == c.MSG_LOI_SHEET


def test_thieu_cot_hien_ten_cot(app_env):
    hong = db.SheetStore(FakeSpreadsheet({
        c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]), c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]),
        c.SHEET_VIEC: FakeWorksheet([[x for x in c.VIEC_COLS if x != c.COL_QUY]])}))
    app_env(store=hong)
    at = mo_app()
    assert not at.exception and c.COL_QUY in at.error[0].value and c.SHEET_VIEC in at.error[0].value


def test_dang_xuat(app_env):
    app_env(tasks=HAI_VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key="logout").click().run()
    assert "user" not in at.session_state and at.text_input(key="login_id") and len(at.tabs) == 0


def test_bi_xoa_khoi_bang_nhan_su_thi_bi_dang_xuat(app_env):
    store, _ = app_env(tasks=HAI_VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    store._spreadsheet.worksheet(c.SHEET_NHAN_SU).rows.pop(2)       # quản lý xóa dòng NV01 trên Sheet
    at.button(key="refresh").click().run()
    assert "user" not in at.session_state and len(at.tabs) == 0
