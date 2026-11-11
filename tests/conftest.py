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


def viec_cho_duyet(**ghi_de):
    """Việc trọng số 3, hạn 20/11, báo cáo 22/11 (trễ 2 ngày), đang chờ duyệt."""
    return viec(**{c.COL_TRANG_THAI: c.TT_CHO_DUYET, c.COL_NGAY_HOAN_THANH: "2026-11-22",
                   c.COL_LINK: "https://a.vn", **ghi_de})


def viec_vi_du_spec(da_duyet=False):
    """Ví dụ ở spec mục 7: NV01 có bốn việc quý 2026-Q4, trọng số 3, 5, 2, 4.

    da_duyet=False: việc 1 còn chờ duyệt (duyệt 5 sao sẽ được 3,24 điểm, KPI 49,57%).
    """
    viec_1 = viec_cho_duyet()
    if da_duyet:
        viec_1 = viec_cho_duyet(**{c.COL_TRANG_THAI: c.TT_HOAN_THANH, c.COL_SAO: "5", c.COL_DIEM: "3.24"})
    return [
        viec_1,
        viec(ID_Viec="V-00000002", Ten_Viec="Việc 2", Trong_So="5", Trang_Thai=c.TT_HOAN_THANH, Diem_KPI_Nhan="2.5"),
        viec(ID_Viec="V-00000003", Ten_Viec="Việc 3", Trong_So="2", Trang_Thai=c.TT_HOAN_THANH, Diem_KPI_Nhan="1.2"),
        viec(ID_Viec="V-00000004", Ten_Viec="Việc 4", Trong_So="4", Trang_Thai=c.TT_DANG_LAM),
    ]


# --- Test giao diện bằng streamlit.testing ---

HOM_NAY = __import__("datetime").date(2026, 11, 11)
APP = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app_env(monkeypatch):
    """Trả về hàm dựng môi trường: app_env(tasks=..., templates=..., nhan_su=...) -> (store, notifier).

    App chạy trên SheetStore với gspread giả và FakeNotifier; "hôm nay" cố định là 2026-11-11.
    """
    import streamlit as st

    import db
    import notifier as notifier_module
    import services

    st.cache_resource.clear()
    st.cache_data.clear()

    def dung(tasks=(), templates=(), nhan_su=NHAN_SU, store=None):
        store = store or make_store(nhan_su, templates=templates, tasks=tasks)
        gia = FakeNotifier()
        monkeypatch.setattr(db, "open_store", lambda secrets: store)
        monkeypatch.setattr(notifier_module, "Notifier", lambda token: gia)
        monkeypatch.setattr(services, "hom_nay", lambda: HOM_NAY)
        return store, gia

    yield dung
    st.cache_resource.clear()
    st.cache_data.clear()


def mo_app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=10)
    at.secrets["telegram_bot_token"] = "token-gia"
    at.secrets["sheet_id"] = "sheet-gia"
    return at.run()


def dang_nhap(at, ident, pin):
    at.text_input(key="login_id").set_value(ident)
    at.text_input(key="login_pin").set_value(pin)
    at.button(key="login_submit").click().run()
    return at


def chu_tren_trang(at):
    """Gom mọi chữ hiển thị trên trang để dò nội dung."""
    nhom = ["markdown", "caption", "error", "warning", "success", "info", "subheader", "header", "title", "code"]
    return " | ".join(str(e.value) for n in nhom for e in getattr(at, n))
