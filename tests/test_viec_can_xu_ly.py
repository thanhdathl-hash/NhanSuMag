"""Khối "Việc cần xử lý": tính trực tiếp từ bảng việc, không lưu thêm gì."""
from datetime import date

import config as c
import services
from tests.conftest import NHAN_SU, nguoi_dung, viec
from tests.fakes import make_store

D = date(2026, 11, 12)
QL, NV1 = nguoi_dung(0), nguoi_dung(1)


def nhom(ds):
    return {g["ma"]: [v[c.COL_ID_VIEC] for v in g["viec"]] for g in ds}


def bang(*dong):
    return make_store(NHAN_SU, tasks=list(dong)).tasks()


def test_quan_ly():
    t = bang(
        viec(ID_Viec="V-1", Trang_Thai=c.TT_CHO_DUYET, Han_Chot="2026-11-01"),
        viec(ID_Viec="V-2", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-10"),      # quá hạn
        viec(ID_Viec="V-3", Trang_Thai=c.TT_MOI_GIAO, Han_Chot="2026-11-12"),      # đến hạn hôm nay
        viec(ID_Viec="V-4", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-13"),      # chưa có gì gấp với quản lý
        viec(ID_Viec="V-5", Trang_Thai=c.TT_HOAN_THANH, Han_Chot="2026-11-01"),
    )
    ds = services.todo_groups(t, QL, D)
    assert nhom(ds) == {c.CXL_CHO_DUYET: ["V-1"], c.CXL_QUA_HAN: ["V-2"], c.CXL_HOM_NAY: ["V-3"]}
    assert [g["ma"] for g in ds] == [c.CXL_CHO_DUYET, c.CXL_QUA_HAN, c.CXL_HOM_NAY]
    assert services.todo_count(ds) == 3
    assert all(g["nhan"] == c.CXL_NHAN[g["ma"]] for g in ds)


def test_nhan_vien_moi_viec_chi_nam_mot_nhom_theo_do_gap():
    t = bang(
        viec(ID_Viec="V-1", Trang_Thai=c.TT_LAM_LAI, Han_Chot="2026-11-10"),       # trả lại và quá hạn -> quá hạn
        viec(ID_Viec="V-2", Trang_Thai=c.TT_LAM_LAI, Han_Chot="2026-11-30"),       # bị trả lại
        viec(ID_Viec="V-3", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-12"),      # hôm nay
        viec(ID_Viec="V-4", Trang_Thai=c.TT_MOI_GIAO, Han_Chot="2026-11-15"),      # trong 3 ngày tới
        viec(ID_Viec="V-5", Trang_Thai=c.TT_MOI_GIAO, Han_Chot="2026-11-16"),      # mới giao, chưa gấp
        viec(ID_Viec="V-6", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-16"),      # đang làm, chưa gấp: không liệt kê
        viec(ID_Viec="V-7", Trang_Thai=c.TT_CHO_DUYET, Han_Chot="2026-11-01"),     # đã nộp
        viec(ID_Viec="V-8", Trang_Thai=c.TT_HOAN_THANH, Han_Chot="2026-11-01"),
    )
    ds = services.todo_groups(t, NV1, D)
    assert nhom(ds) == {c.CXL_QUA_HAN: ["V-1"], c.CXL_LAM_LAI: ["V-2"], c.CXL_HOM_NAY: ["V-3"],
                        c.CXL_SAP_DEN_HAN: ["V-4"], c.CXL_MOI_GIAO: ["V-5"]}
    assert [g["ma"] for g in ds] == [c.CXL_QUA_HAN, c.CXL_LAM_LAI, c.CXL_HOM_NAY, c.CXL_SAP_DEN_HAN, c.CXL_MOI_GIAO]
    assert services.todo_count(ds) == 5


def test_khong_co_gi_thi_rong():
    assert services.todo_groups(bang(), QL, D) == []
    assert services.todo_groups(bang(viec(Trang_Thai=c.TT_HOAN_THANH)), NV1, D) == []
    assert services.todo_count([]) == 0


def test_han_chot_hong_khong_lam_sap():
    t = bang(viec(ID_Viec="V-1", Trang_Thai=c.TT_MOI_GIAO, Han_Chot="20/11"),
             viec(ID_Viec="V-2", Trang_Thai=c.TT_LAM_LAI, Han_Chot=""))
    assert nhom(services.todo_groups(t, NV1, D)) == {c.CXL_LAM_LAI: ["V-2"], c.CXL_MOI_GIAO: ["V-1"]}
    assert services.todo_groups(t, QL, D) == []


def test_trong_moi_nhom_xep_theo_han_chot():
    t = bang(viec(ID_Viec="V-1", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-09"),
             viec(ID_Viec="V-2", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-03"))
    assert nhom(services.todo_groups(t, QL, D))[c.CXL_QUA_HAN] == ["V-2", "V-1"]
