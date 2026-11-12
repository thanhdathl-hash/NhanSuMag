"""Các lỗi do rà soát cuối nhánh tìm ra: Sheet bị sửa tay và lỗi cài đặt lần đầu."""
from datetime import date

import google.auth.exceptions
import gspread
import pytest

import config as c
import db
import services
from tests.conftest import NHAN_SU, chu_tren_trang, dang_nhap, mo_app, viec, viec_cho_duyet
from tests.fakes import make_store

D = date(2026, 11, 22)
ID = "V-00000001"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
HAI_QL = NHAN_SU + [{**NHAN_SU[0], c.COL_ID_NV: "QL02", c.COL_SDT: "0900000002"}]


# --- db: khoảng trắng thừa và lỗi cài đặt ---

def test_o_co_khoang_trang_thua_duoc_cat():
    s = make_store([{**NHAN_SU[1], c.COL_ID_NV: "NV01 "}], tasks=[viec(Trang_Thai="Mới giao ", Nguoi_Nhan=" NV01")])
    assert s.employees().iloc[0][c.COL_ID_NV] == "NV01"
    t = s.tasks().iloc[0]
    assert (t[c.COL_TRANG_THAI], t[c.COL_NGUOI_NHAN]) == (c.TT_MOI_GIAO, "NV01")


def test_chua_chia_se_sheet_bao_ro_nguyen_nhan():
    s = make_store(NHAN_SU)
    s._spreadsheet.worksheet(c.SHEET_VIEC).fail_with = PermissionError("403")
    with pytest.raises(db.StoreError, match="chia sẻ"):
        s.tasks()
    with pytest.raises(db.StoreError, match="chia sẻ"):
        s.update_task(ID, {c.COL_TRANG_THAI: c.TT_DANG_LAM})


def test_loi_xac_thuc_google_thanh_store_error():
    s = make_store(NHAN_SU)
    s._spreadsheet.worksheet(c.SHEET_VIEC).fail_with = google.auth.exceptions.RefreshError("x")
    with pytest.raises(db.StoreError):
        s.tasks()


@pytest.mark.parametrize("loi, khop", [(ValueError("Unable to load PEM file"), "secrets"),
                                       (PermissionError("403"), "chia sẻ"),
                                       (google.auth.exceptions.RefreshError("x"), "Google")])
def test_open_store_loi_cai_dat(monkeypatch, loi, khop):
    def hong(info):
        raise loi
    monkeypatch.setattr(gspread, "service_account_from_dict", hong)
    with pytest.raises(db.StoreError, match=khop):
        db.open_store({"gcp_service_account": {}, "sheet_id": "x"})


def test_open_store_thieu_khoa_secrets():
    with pytest.raises(db.StoreError, match="secrets"):
        db.open_store({})


# --- services: chuẩn bị dữ liệu và cảnh báo về Sheet ---

def test_prepare_tasks_bo_dong_trung_id_va_thieu_id():
    s = make_store(NHAN_SU, tasks=[viec(), viec(Ten_Viec="Bản chép"), viec(ID_Viec="", Ten_Viec="Thiếu mã"),
                                   viec(ID_Viec="V-00000002")])
    sach = services.prepare_tasks(s.tasks())
    assert list(sach[c.COL_ID_VIEC]) == [ID, "V-00000002"] and sach.iloc[0][c.COL_TEN_VIEC] == "Việc A"
    cb = " | ".join(services.sheet_warnings(s.tasks(), s.employees()))
    assert ID in cb and "trùng" in cb and c.COL_ID_VIEC in cb and "1 dòng" in cb


def test_prepare_tasks_quy_theo_han_chot():
    s = make_store(NHAN_SU, tasks=[
        viec(Quy="", Thang=""),                                               # thêm tay, quên điền quý
        viec(ID_Viec="V-00000002", Han_Chot="2027-01-15"),                    # dời hạn, quên sửa quý
        viec(ID_Viec="V-00000003", Han_Chot="15/01/2027", Quy="2026-Q4"),     # ngày hỏng: giữ ô Quy
    ])
    sach = services.prepare_tasks(s.tasks())
    assert list(sach[c.COL_QUY]) == ["2026-Q4", "2027-Q1", "2026-Q4"]
    assert list(sach[c.COL_THANG])[:2] == ["2026-11", "2027-01"]


def test_kpi_quy_tinh_ca_viec_thieu_o_quy(notifier, ql):
    s = make_store(NHAN_SU, tasks=[viec_cho_duyet(Ngay_Hoan_Thanh="2026-11-20"),
                                   viec(ID_Viec="V-00000002", Trong_So="3", Quy="", Thang="")])
    services.approve_task(s, notifier, ql, ID, stars=4, today=date(2026, 12, 1))
    assert s.employees().iloc[1][c.COL_KPI_QUY] == "50.0"                    # 3 / (3 + 3)
    assert services.employee_kpi(services.prepare_tasks(s.tasks()), "NV01", "2026-Q4") == (50.0, 1, 2)


def test_sheet_warnings_sach_thi_rong():
    s = make_store(NHAN_SU, tasks=[viec()])
    assert services.sheet_warnings(s.tasks(), s.employees()) == []


@pytest.mark.parametrize("nhan_su", [NHAN_SU[1:], HAI_QL])
def test_sheet_warnings_so_quan_ly(nhan_su):                                  # Review Focus 4
    s = make_store(nhan_su)
    assert any(c.ROLE_QUAN_LY in w for w in services.sheet_warnings(s.tasks(), s.employees()))


def test_sheet_warnings_trang_thai_la():
    s = make_store(NHAN_SU, tasks=[viec(Trang_Thai="Xong")])
    assert any("Xong" in w and ID in w for w in services.sheet_warnings(s.tasks(), s.employees()))


# --- services: không có đúng một quản lý ---

def test_bao_cao_link_khi_co_hai_quan_ly_thi_luu_va_noi_ro(notifier, nv1):
    s = make_store(HAI_QL, tasks=[viec(Trang_Thai=c.TT_DANG_LAM)])
    r = services.submit_task(s, notifier, nv1, ID, today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
    assert r.notified is False and c.ROLE_QUAN_LY in r.warning and notifier.sent == []


def test_bao_cao_anh_khi_co_hai_quan_ly_thi_bao_dung_nguyen_nhan(notifier, nv1):
    s = make_store(HAI_QL, tasks=[viec(Trang_Thai=c.TT_DANG_LAM)])
    with pytest.raises(services.ServiceError, match=c.ROLE_QUAN_LY):
        services.submit_task(s, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and notifier.sent == []


# --- services: bấm "Giao việc" hai lần ---

def tao(store, notifier, ql, **kw):
    mac_dinh = dict(ten_viec="Báo cáo tuần", mo_ta="", nguoi_nhan="NV01", han_chot=date(2026, 12, 1), trong_so=3, today=D)
    return services.create_task(store, notifier, ql, **{**mac_dinh, **kw})


def test_giao_trung_trong_ngay_bi_tu_choi(store, notifier, ql):
    tao(store, notifier, ql)
    with pytest.raises(services.InvalidInput, match="vừa được giao"):
        tao(store, notifier, ql, ten_viec=" Báo cáo tuần ")
    assert len(store.tasks()) == 1 and len(notifier.sent) == 1


@pytest.mark.parametrize("kw", [{"ten_viec": "Báo cáo tháng"}, {"nguoi_nhan": "NV02"},
                                {"han_chot": date(2026, 12, 2)}, {"today": date(2026, 11, 23)}])
def test_giao_viec_khac_di_mot_chut_thi_duoc(store, notifier, ql, kw):
    tao(store, notifier, ql)
    tao(store, notifier, ql, **kw)
    assert len(store.tasks()) == 2


def test_viec_da_bat_dau_thi_giao_lai_cung_ten_duoc(store, notifier, ql, nv1):
    r = tao(store, notifier, ql)
    services.start_task(store, nv1, r.task[c.COL_ID_VIEC])
    tao(store, notifier, ql)
    assert len(store.tasks()) == 2


# --- giao diện ---

def test_trung_id_viec_khong_lam_sap_man_hinh(app_env):
    app_env(tasks=[viec(), viec(Ten_Viec="Bản chép"), viec_cho_duyet(ID_Viec="V-00000002"),
                   viec_cho_duyet(ID_Viec="V-00000002"), viec(ID_Viec=""), viec(ID_Viec="")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception and "Việc A" in chu_tren_trang(at)
    at.button(key="logout").click().run()
    dang_nhap(at, "QL01", "1111")
    assert not at.exception
    assert any(ID in w.value and "trùng" in w.value for w in at.warning)


def test_nhan_vien_khong_thay_canh_bao_ve_sheet(app_env):
    app_env(tasks=[viec(), viec(Ten_Viec="Bản chép")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert len(at.warning) == 0


def test_hai_quan_ly_thi_hien_canh_bao(app_env):
    app_env(nhan_su=HAI_QL)
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and any(c.ROLE_QUAN_LY in w.value for w in at.warning)


def test_chua_chia_se_sheet_hien_huong_dan(app_env):
    store, _ = app_env()
    store._spreadsheet.worksheet(c.SHEET_NHAN_SU).fail_with = PermissionError("403")
    at = mo_app()
    assert not at.exception and "chia sẻ" in at.error[0].value


def test_doi_ten_cot_giua_chung_bao_ten_cot(app_env):
    store, _ = app_env(tasks=[viec()])
    at = dang_nhap(mo_app(), "NV01", "1234")
    ws = store._spreadsheet.worksheet(c.SHEET_VIEC)
    ws.rows[0][c.VIEC_COLS.index(c.COL_TRANG_THAI)] = "TrangThai"
    at.button(key=f"start_{ID}").click().run()
    assert not at.exception and c.COL_TRANG_THAI in chu_tren_trang(at)


def test_bao_cao_khi_thieu_quan_ly_hien_canh_bao_ro(app_env):
    store, _ = app_env(tasks=[viec(Trang_Thai=c.TT_DANG_LAM)], nhan_su=NHAN_SU[1:])
    at = dang_nhap(mo_app(), "NV01", "1234")
    at.button(key=f"nop_{ID}").click().run()
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
    assert any(c.ROLE_QUAN_LY in w.value for w in at.warning)
