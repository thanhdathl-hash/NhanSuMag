import pytest

import config as c
from tests.fakes import FakeNotifier, make_store

NHAN_SU = [
    {c.COL_ID_NV: "QL01", c.COL_TEN: "Trần Quản Lý", c.COL_SDT: "0900000001", c.COL_MA_PIN: "1111",
     c.COL_CHAT_ID: "100", c.COL_ROLE: c.ROLE_QUAN_LY, c.COL_KPI_QUY: ""},
    {c.COL_ID_NV: "NV01", c.COL_TEN: "Nguyễn An", c.COL_SDT: "0912345678", c.COL_MA_PIN: "1234",
     c.COL_CHAT_ID: "201", c.COL_ROLE: c.ROLE_NHAN_VIEN, c.COL_KPI_QUY: ""},
    {c.COL_ID_NV: "NV02", c.COL_TEN: "Lê Bình", c.COL_SDT: "0987654321", c.COL_MA_PIN: "5678",
     c.COL_CHAT_ID: "", c.COL_ROLE: c.ROLE_NHAN_VIEN, c.COL_KPI_QUY: ""},
]


def viec(**ghi_de):
    """Một dòng việc đủ cột. Ghi đè bằng tên cột, ví dụ viec(Trang_Thai=c.TT_DANG_LAM)."""
    d = {k: "" for k in c.VIEC_COLS}
    d.update({
        c.COL_ID_VIEC: "V-00000001", c.COL_TEN_VIEC: "Việc A", c.COL_NGUOI_NHAN: "NV01",
        c.COL_TRONG_SO: "3", c.COL_NGAY_GIAO: "2026-11-01", c.COL_HAN_CHOT: "2026-11-20",
        c.COL_TRANG_THAI: c.TT_MOI_GIAO, c.COL_THANG: "2026-11", c.COL_QUY: "2026-Q4",
    })
    d.update(ghi_de)
    return d


def nguoi_dung(i):
    return {k: v for k, v in NHAN_SU[i].items() if k != c.COL_MA_PIN}


@pytest.fixture
def store():
    return make_store(NHAN_SU)


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def ql():
    return nguoi_dung(0)


@pytest.fixture
def nv1():
    return nguoi_dung(1)


@pytest.fixture
def nv2():
    return nguoi_dung(2)
