import pytest
import requests

import config as c
import db
from tests.conftest import NHAN_SU, viec
from tests.fakes import FakeSpreadsheet, FakeWorksheet, make_store


def test_doc_tra_ve_chuoi_va_du_cot():                      # Review Focus 1
    s = make_store(NHAN_SU, tasks=[viec(Trong_So=3, Diem_KPI_Nhan=3.24)])   # ô số trên Sheet
    t = s.tasks().iloc[0]
    assert t[c.COL_TRONG_SO] == "3" and t[c.COL_DIEM] == "3.24"
    assert t[c.COL_GHI_CHU_QL] == ""                         # ô trống cuối dòng bị gspread cắt
    assert list(s.tasks().columns) == c.VIEC_COLS


def test_so_nguyen_dang_float_doc_thanh_chuoi_nguyen():
    s = make_store(NHAN_SU, tasks=[viec(Trong_So=3.0)])
    assert s.tasks().iloc[0][c.COL_TRONG_SO] == "3"


def test_sdt_giu_so_0_dau():
    assert make_store(NHAN_SU).employees().iloc[1][c.COL_SDT] == "0912345678"


def test_bang_viec_trong_van_co_du_cot():
    assert list(make_store(NHAN_SU).tasks().columns) == c.VIEC_COLS


def test_dung_cot_thi_check_headers_khong_loi():
    make_store(NHAN_SU).check_headers()


def test_thieu_cot_bao_dung_ten():
    ws = FakeWorksheet([[x for x in c.VIEC_COLS if x not in (c.COL_QUY, c.COL_THANG)]])
    s = db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
                                       c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]), c.SHEET_VIEC: ws}))
    with pytest.raises(db.SchemaError, match="Data_Giao_Viec.*Quy.*Thang"):
        s.check_headers()


def test_thieu_bang_bao_ten_bang():
    with pytest.raises(db.SchemaError, match="Thu_Vien_Mau"):
        db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
                                       c.SHEET_VIEC: FakeWorksheet([c.VIEC_COLS])})).check_headers()


def test_cot_xep_thu_tu_khac_van_doc_ghi_dung():
    dao = list(reversed(c.VIEC_COLS))
    d = viec()
    s = db.SheetStore(FakeSpreadsheet({
        c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]), c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]),
        c.SHEET_VIEC: FakeWorksheet([dao, [d[k] for k in dao]])}))
    s.update_task("V-00000001", {c.COL_TRANG_THAI: c.TT_DANG_LAM})
    assert s.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_DANG_LAM
    assert s.get_task("V-00000001")[c.COL_TEN_VIEC] == d[c.COL_TEN_VIEC]
    s.append_task(viec(ID_Viec="V-00000002", Ten_Viec="Việc B"))
    assert s.get_task("V-00000002")[c.COL_TEN_VIEC] == "Việc B"


def test_them_roi_sua_viec():
    s = make_store(NHAN_SU)
    s.append_task(viec())
    s.append_task(viec(ID_Viec="V-00000002"))
    s.update_task("V-00000002", {c.COL_TRANG_THAI: c.TT_CHO_DUYET, c.COL_LINK: "https://a.vn"})
    assert s.get_task("V-00000002")[c.COL_LINK] == "https://a.vn"
    assert s.get_task("V-00000002")[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
    assert s.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_MOI_GIAO


def test_gia_tri_bat_dau_bang_dau_bang_duoc_luu_nguyen_van():     # RAW, không thành công thức
    s = make_store(NHAN_SU)
    s.append_task(viec(Ten_Viec="=1+1"))
    assert s.get_task("V-00000001")[c.COL_TEN_VIEC] == "=1+1"


def test_khong_tim_thay_viec():
    s = make_store(NHAN_SU)
    assert s.get_task("V-khongco") is None
    with pytest.raises(db.TaskNotFound):
        s.update_task("V-khongco", {c.COL_TRANG_THAI: c.TT_DANG_LAM})


def test_cap_nhat_kpi_quy_nhan_vien():
    s = make_store(NHAN_SU)
    s.update_employee("NV01", {c.COL_KPI_QUY: "49.57"})
    assert s.employees().iloc[1][c.COL_KPI_QUY] == "49.57"
    assert s.employees().iloc[0][c.COL_KPI_QUY] == ""


def test_mat_mang_thanh_store_error():
    s = make_store(NHAN_SU)
    s._spreadsheet.worksheet(c.SHEET_VIEC).fail_with = requests.ConnectionError("x")
    with pytest.raises(db.StoreError, match=c.MSG_LOI_SHEET):
        s.tasks()
    with pytest.raises(db.StoreError):
        s.append_task(viec())
