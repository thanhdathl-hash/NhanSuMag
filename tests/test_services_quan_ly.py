from datetime import date

import pytest

import config as c
import db
import services
from tests.conftest import NHAN_SU, viec, viec_cho_duyet, viec_vi_du_spec
from tests.fakes import make_store

D = date(2026, 12, 1)
ID = "V-00000001"


@pytest.fixture
def store():
    return make_store(NHAN_SU, tasks=[viec_cho_duyet()])


def kpi_quy(store, i=1):
    return store.employees().iloc[i][c.COL_KPI_QUY]


# --- Duyệt ---

def test_duyet_ghi_sao_va_diem(store, notifier, ql):
    r = services.approve_task(store, notifier, ql, ID, stars=5, today=D)
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_SAO], t[c.COL_DIEM]) == (c.TT_HOAN_THANH, "5", "3.24")   # 3 × 0,90 × 1,2
    assert r.task[c.COL_DIEM] == "3.24" and r.kpi_saved is True
    assert r.notified and notifier.sent[0][0] == "201" and "3.24" in notifier.sent[0][1]           # T4 tới nhân viên


def test_cho_duyet_lau_khong_bi_tinh_tre(notifier, ql):
    s = make_store(NHAN_SU, tasks=[viec_cho_duyet(Ngay_Hoan_Thanh="2026-11-20")])
    services.approve_task(s, notifier, ql, ID, stars=4, today=date(2026, 12, 20))
    assert s.get_task(ID)[c.COL_DIEM] == "3.0"


def test_duyet_cap_nhat_kpi_quy_hien_tai(notifier, ql):
    s = make_store(NHAN_SU, tasks=viec_vi_du_spec())
    services.approve_task(s, notifier, ql, ID, stars=5, today=D)
    assert kpi_quy(s) == "49.57"
    assert kpi_quy(s, 2) == ""                                  # NV02 không bị đụng tới


def test_kpi_quy_chi_tinh_viec_cua_quy_hien_tai_va_cua_nguoi_do(notifier, ql):
    them = [
        viec(ID_Viec="V-0000000a", Nguoi_Nhan="NV02", Trong_So="5", Trang_Thai=c.TT_HOAN_THANH, Diem_KPI_Nhan="5.0"),
        viec(ID_Viec="V-0000000b", Trong_So="5", Trang_Thai=c.TT_HOAN_THANH, Diem_KPI_Nhan="6.0",
             Han_Chot="2026-09-10", Thang="2026-09", Quy="2026-Q3"),
    ]
    s = make_store(NHAN_SU, tasks=viec_vi_du_spec() + them)
    services.approve_task(s, notifier, ql, ID, stars=5, today=D)
    assert kpi_quy(s) == "49.57"


def test_duyet_viec_quy_truoc_khi_quy_nay_chua_co_viec(notifier, ql):
    s = make_store(NHAN_SU, tasks=[viec_cho_duyet()])
    r = services.approve_task(s, notifier, ql, ID, stars=4, today=date(2027, 1, 5))
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_HOAN_THANH
    assert kpi_quy(s) == "" and r.kpi_saved is True


@pytest.mark.parametrize("stars", [0, 6, None, 4.5, "5", True])
def test_sao_khong_hop_le(store, notifier, ql, stars):
    with pytest.raises(services.InvalidInput):
        services.approve_task(store, notifier, ql, ID, stars=stars, today=D)
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET and notifier.sent == []


@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_DANG_LAM, c.TT_LAM_LAI, c.TT_HOAN_THANH])
def test_duyet_va_tra_lai_sai_trang_thai(notifier, ql, tu):
    s = make_store(NHAN_SU, tasks=[viec_cho_duyet(Trang_Thai=tu)])
    with pytest.raises(services.InvalidState):
        services.approve_task(s, notifier, ql, ID, stars=4, today=D)
    with pytest.raises(services.InvalidState):
        services.return_task(s, notifier, ql, ID, ly_do="x")
    assert s.get_task(ID)[c.COL_TRANG_THAI] == tu and notifier.sent == []


def test_duyet_hai_lan_khong_cong_doi(store, notifier, ql):     # Review Focus 4
    services.approve_task(store, notifier, ql, ID, stars=5, today=D)
    with pytest.raises(services.InvalidState):
        services.approve_task(store, notifier, ql, ID, stars=1, today=D)
    assert store.get_task(ID)[c.COL_DIEM] == "3.24" and len(notifier.sent) == 1


def test_nhan_vien_khong_tu_duyet(store, notifier, nv1):
    with pytest.raises(services.PermissionDenied):
        services.approve_task(store, notifier, nv1, ID, stars=5, today=D)
    with pytest.raises(services.PermissionDenied):
        services.return_task(store, notifier, nv1, ID, ly_do="x")
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_viec_khong_ton_tai(store, notifier, ql):                # Review Focus 4
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.approve_task(store, notifier, ql, "V-khongco", stars=5, today=D)
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.return_task(store, notifier, ql, "V-khongco", ly_do="x")


@pytest.mark.parametrize("cot, gia_tri", [
    (c.COL_NGAY_HOAN_THANH, ""), (c.COL_NGAY_HOAN_THANH, "22/11/2026"), (c.COL_HAN_CHOT, "46346"),
    (c.COL_TRONG_SO, "abc"), (c.COL_TRONG_SO, ""), (c.COL_TRONG_SO, "9"),
])
def test_o_bi_sua_tay_hong_thi_bao_ro_o_nao(notifier, ql, cot, gia_tri):     # Review Focus 1
    s = make_store(NHAN_SU, tasks=[viec_cho_duyet(**{cot: gia_tri})])
    with pytest.raises(services.ServiceError, match=cot):
        services.approve_task(s, notifier, ql, ID, stars=4, today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_ghi_kpi_quy_loi_thi_viec_van_duoc_duyet(store, notifier, ql, monkeypatch):
    def hong(*a, **k):
        raise db.StoreError("x")
    monkeypatch.setattr(store, "update_employee", hong)
    r = services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert r.kpi_saved is False and store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_HOAN_THANH
    assert r.notified is True


def test_duyet_telegram_loi_van_luu(store, notifier, ql):
    notifier.ok = False
    r = services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert r.notified is False and store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_HOAN_THANH


# --- Trả lại ---

def test_tra_lai(store, notifier, ql):
    r = services.return_task(store, notifier, ql, ID, ly_do=" Thiếu số liệu ")
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_GHI_CHU_QL]) == (c.TT_LAM_LAI, "Thiếu số liệu")
    assert r.notified and "Thiếu số liệu" in notifier.sent[0][1] and notifier.sent[0][0] == "201"
    assert t[c.COL_DIEM] == "" and t[c.COL_SAO] == ""


@pytest.mark.parametrize("ly_do", ["", "   ", None])
def test_tra_lai_thieu_ly_do(store, notifier, ql, ly_do):
    with pytest.raises(services.InvalidInput):
        services.return_task(store, notifier, ql, ID, ly_do=ly_do)
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_tra_lai_roi_nop_lai_tinh_tre_theo_lan_cuoi(store, notifier, ql, nv1):
    services.return_task(store, notifier, ql, ID, ly_do="Sửa lại")
    services.submit_task(store, notifier, nv1, ID, today=date(2026, 11, 24))   # trễ 4 ngày
    services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert store.get_task(ID)[c.COL_DIEM] == "2.4"                                                   # 3 × 0,80 × 1,0


def test_mat_mang_sau_khi_ghi_thi_van_tinh_la_da_luu(store, notifier, ql):
    import requests
    store._spreadsheet.worksheet(c.SHEET_NHAN_SU).fail_with = requests.ConnectionError("x")
    r = services.return_task(store, notifier, ql, ID, ly_do="Sửa lại")
    assert r.notified is False and store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_LAM_LAI
