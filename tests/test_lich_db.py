"""db.py: bảng Lich_Ca_Nhan và cột Lich_Google."""
import pytest

import config as c
import db
from tests.conftest import NHAN_SU, lich
from tests.fakes import make_store


def test_cot_bang_lich_va_cot_lich_google():
    assert c.LICH_COLS == ["ID_Lich", "ID_NV", "Noi_Dung", "Ngay", "Gio_Bat_Dau", "Gio_Ket_Thuc", "Lap", "Lap_Den", "Da_Xong"]
    assert c.NHAN_SU_COLS[-1] == "Lich_Google" and c.SHEET_LICH == "Lich_Ca_Nhan"
    assert c.SHEET_COLS[c.SHEET_LICH] == c.LICH_COLS and c.SHEET_KEY[c.SHEET_LICH] == c.COL_ID_LICH
    assert c.LAP_KIEU == ["Không lặp", "Hằng ngày", "Hằng tuần"]


def test_doc_bang_lich_trong_van_du_cot():
    s = make_store(NHAN_SU)
    assert list(s.personal().columns) == c.LICH_COLS and len(s.personal()) == 0
    s.check_headers()


def test_them_doc_sua_xoa():
    s = make_store(NHAN_SU)
    s.append_personal(lich())
    s.append_personal(lich(ID_Lich="L-00000002", Noi_Dung="Tập thể dục"))
    s.append_personal(lich(ID_Lich="L-00000003", Noi_Dung="Đọc sách"))
    assert s.get_personal("L-00000002")[c.COL_NOI_DUNG] == "Tập thể dục"
    s.update_personal("L-00000002", {c.COL_DA_XONG: "2026-11-12"})
    assert s.get_personal("L-00000002")[c.COL_DA_XONG] == "2026-11-12"
    s.delete_personal("L-00000002")
    assert list(s.personal()[c.COL_ID_LICH]) == ["L-00000001", "L-00000003"]
    assert s.get_personal("L-00000002") is None


def test_xoa_muc_khong_ton_tai():
    s = make_store(NHAN_SU)
    with pytest.raises(db.TaskNotFound):
        s.delete_personal("L-khongco")
    with pytest.raises(db.TaskNotFound):
        s.update_personal("L-khongco", {c.COL_DA_XONG: ""})


def test_thieu_bang_lich_bao_ten_bang():
    from tests.fakes import FakeSpreadsheet, FakeWorksheet
    s = db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
                                       c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]),
                                       c.SHEET_VIEC: FakeWorksheet([c.VIEC_COLS])}))
    with pytest.raises(db.SchemaError, match="Lich_Ca_Nhan"):
        s.check_headers()


def test_gio_luu_dang_so_tren_sheet_khong_lam_sap():
    s = make_store(NHAN_SU, personal=[lich(Gio_Bat_Dau=0.354166)])      # ô không đặt định dạng văn bản
    assert isinstance(s.personal().iloc[0][c.COL_GIO_BAT_DAU], str)
