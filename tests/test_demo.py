"""Chế độ chạy thử: `streamlit run demo.py`, không cần Sheet, service account hay bot."""
import pathlib
from datetime import date

import pytest

import config as c
import db
import notifier
import services
from tests.conftest import chu_tren_trang, dang_nhap, html_tren_trang

DEMO = str(pathlib.Path(__file__).resolve().parent.parent / "demo.py")


@pytest.fixture
def mo_demo(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    # demo.py thay db.open_store và notifier.from_secrets; monkeypatch trả lại bản gốc sau test
    monkeypatch.setattr(db, "open_store", db.open_store)
    monkeypatch.setattr(notifier, "from_secrets", notifier.from_secrets)
    monkeypatch.setattr(services, "hom_nay", lambda: date(2026, 11, 11))   # dữ liệu mẫu tính theo "hôm nay"
    st.cache_resource.clear()
    st.cache_data.clear()
    yield lambda: AppTest.from_file(DEMO, default_timeout=15).run()     # không có secrets nào
    st.cache_resource.clear()
    st.cache_data.clear()


def test_chay_duoc_khi_khong_co_secrets_va_noi_ro_la_chay_thu(mo_demo):
    at = mo_demo()
    assert not at.exception
    chu = chu_tren_trang(at)
    assert "chạy thử" in chu.lower() and "QL01" in chu and "1111" in chu      # có sẵn tài khoản mẫu
    assert at.text_input(key="login_id")


def test_quan_ly_thay_du_lieu_mau(mo_demo):
    at = dang_nhap(mo_demo(), "QL01", "1111")
    assert not at.exception and len(at.tabs) == 4
    assert len(at.warning) == 1 and "chạy thử" in at.warning[0].value.lower()   # dữ liệu mẫu sạch, chỉ có băng báo chạy thử
    assert sum(1 for b in at.button if (b.key or "").startswith("lv_")) >= 6     # lịch có việc ở nhiều ngày
    assert len(at.get("image")) == 1                                             # một việc chờ duyệt có ảnh chứng minh
    assert any(k.startswith("duyet_") for k in (b.key or "" for b in at.button))


def test_nhan_vien_thay_viec_va_kpi(mo_demo):
    at = dang_nhap(mo_demo(), "NV01", "1234")
    assert not at.exception and len(at.tabs) == 2
    assert len(at.metric) == 1 and at.metric[0].value.endswith("%")
    assert any((b.key or "").startswith("start_") for b in at.button)
    assert "Lý do trả lại" in chu_tren_trang(at)


def test_giao_viec_trong_chay_thu_hien_tin_telegram_gia_lap(mo_demo):
    at = dang_nhap(mo_demo(), "QL01", "1111")
    at.text_input(key="gv_ten").set_value("Việc thử nghiệm")
    at.selectbox(key="gv_nguoi_nhan").set_value("NV02")
    at.button(key="gv_submit").click().run()
    assert not at.exception and at.success[0].value == c.MSG_DA_LUU
    assert "Việc thử nghiệm" in chu_tren_trang(at)                # tin T1 giả lập hiện ở thanh bên
    at.button(key="logout").click().run()
    dang_nhap(at, "NV02", "1234")
    assert "Việc thử nghiệm" in chu_tren_trang(at)                # dữ liệu dùng chung giữa các phiên


def test_demo_khong_dung_gspread_that(mo_demo, monkeypatch):
    import gspread

    def cam(*a, **k):
        raise AssertionError("chế độ chạy thử không được gọi Google")
    monkeypatch.setattr(gspread, "service_account_from_dict", cam)
    at = dang_nhap(mo_demo(), "QL01", "1111")
    assert not at.exception
