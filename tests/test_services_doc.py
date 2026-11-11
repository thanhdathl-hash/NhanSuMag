from datetime import date

import pandas as pd
import pytest

import config as c
import services
from tests.conftest import NHAN_SU, viec, viec_vi_du_spec
from tests.fakes import make_store

D = date(2026, 11, 25)


@pytest.fixture
def kho():
    return make_store(NHAN_SU, tasks=viec_vi_du_spec(da_duyet=True))


def test_kpi_table(kho):
    b = services.kpi_table(kho.tasks(), kho.employees(), "2026-Q4").set_index(c.COL_ID_NV)
    assert list(b.index) == ["NV01", "NV02"]                    # không có dòng quản lý
    assert b.loc["NV01", c.COL_TEN] == "Nguyễn An"
    assert (b.loc["NV01", c.KQ_KPI], b.loc["NV01", c.KQ_HOAN_THANH], b.loc["NV01", c.KQ_TONG_VIEC]) == (49.57, 3, 4)
    assert b.loc["NV02", c.KQ_KPI] is None and b.loc["NV02", c.KQ_TONG_VIEC] == 0


def test_kpi_table_quy_khac_thi_trong(kho):
    b = services.kpi_table(kho.tasks(), kho.employees(), "2026-Q3")
    assert list(b[c.KQ_KPI]) == [None, None] and list(b[c.KQ_TONG_VIEC]) == [0, 0]


def test_employee_kpi(kho):
    assert services.employee_kpi(kho.tasks(), "NV01", "2026-Q4") == (49.57, 3, 4)
    assert services.employee_kpi(kho.tasks(), "NV02", "2026-Q4") == (None, 0, 0)


def test_overdue():
    qua, nay = "2026-11-24", "2026-11-25"
    s = make_store(NHAN_SU, tasks=[
        viec(ID_Viec="V-1", Han_Chot=qua, Trang_Thai=c.TT_DANG_LAM),
        viec(ID_Viec="V-2", Han_Chot=qua, Trang_Thai=c.TT_MOI_GIAO),
        viec(ID_Viec="V-3", Han_Chot=qua, Trang_Thai=c.TT_LAM_LAI),
        viec(ID_Viec="V-4", Han_Chot=nay, Trang_Thai=c.TT_DANG_LAM),          # đến hạn hôm nay: chưa quá hạn
        viec(ID_Viec="V-5", Han_Chot=qua, Trang_Thai=c.TT_CHO_DUYET),
        viec(ID_Viec="V-6", Han_Chot=qua, Trang_Thai=c.TT_HOAN_THANH),
        viec(ID_Viec="V-7", Han_Chot="abc", Trang_Thai=c.TT_DANG_LAM),        # Review Focus 1
        viec(ID_Viec="V-8", Han_Chot="", Trang_Thai=c.TT_DANG_LAM),
        viec(ID_Viec="V-9", Han_Chot="2026-9-1", Trang_Thai=c.TT_DANG_LAM),   # sai định dạng: bỏ qua
    ])
    assert list(services.overdue_tasks(s.tasks(), D)[c.COL_ID_VIEC]) == ["V-1", "V-2", "V-3"]


def test_overdue_bang_trong():
    assert len(services.overdue_tasks(make_store(NHAN_SU).tasks(), D)) == 0


def test_status_counts(kho):
    assert services.status_counts(kho.tasks()) == {
        c.TT_MOI_GIAO: 0, c.TT_DANG_LAM: 1, c.TT_CHO_DUYET: 0, c.TT_HOAN_THANH: 3, c.TT_LAM_LAI: 0}
    assert services.status_counts(make_store(NHAN_SU).tasks()) == {t: 0 for t in c.TRANG_THAI}


def test_quarters():
    s = make_store(NHAN_SU, tasks=[viec(Quy="2026-Q3"), viec(ID_Viec="V-2", Quy="2026-Q4"),
                                   viec(ID_Viec="V-3", Quy="2026-Q4"), viec(ID_Viec="V-4", Quy="")])
    assert services.quarters(s.tasks(), date(2027, 1, 2)) == ["2027-Q1", "2026-Q4", "2026-Q3"]
    assert services.quarters(s.tasks(), date(2026, 11, 2)) == ["2026-Q4", "2026-Q3"]
    assert services.quarters(make_store(NHAN_SU).tasks(), date(2026, 11, 2)) == ["2026-Q4"]
