from datetime import datetime, timedelta, timezone

import pytest

import auth
import config as c
from tests.conftest import NHAN_SU
from tests.fakes import make_store

T0 = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)


def ns(them=()):
    return make_store(list(NHAN_SU) + list(them)).employees()


def vao(ident, pin, guard=None, now=T0, bang=None):
    return auth.authenticate(ns() if bang is None else bang, ident, pin, guard or auth.LoginGuard(), now)


@pytest.mark.parametrize("raw", ["0912345678", "0912 345 678", "0912.345.678", "+84912345678",
                                 "+84 912.345.678", "84912345678", "912345678", " 0912345678 ",
                                 "0912-345-678"])
def test_chuan_hoa_sdt(raw):                                   # Review Focus 3
    assert auth.normalize_phone(raw) == "0912345678"


@pytest.mark.parametrize("ident", ["NV01", "nv01", " NV01 ", "0912345678", "+84 912 345 678"])
def test_dung_pin(ident):
    r = vao(ident, "1234")
    assert r.error is None and r.user[c.COL_ID_NV] == "NV01" and c.COL_MA_PIN not in r.user


def test_sdt_tren_sheet_mat_so_0_van_khop():                   # Review Focus 3
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03", c.COL_SDT: 933333333}])   # Sheet lưu thành số
    assert vao("0933333333", "1234", bang=bang).user[c.COL_ID_NV] == "NV03"


def test_sai_pin_va_id_khong_ton_tai_cung_mot_thong_bao():
    assert vao("NV01", "0000").error == vao("NV99", "0000").error == c.MSG_DANG_NHAP_SAI
    assert vao("NV01", "0000").user is None


@pytest.mark.parametrize("ident, pin", [("", ""), ("   ", "1234"), ("NV01", "")])
def test_de_trong_thi_tu_choi(ident, pin):
    assert vao(ident, pin).user is None


def test_pin_trong_tren_sheet_khong_dang_nhap_duoc():          # Review Focus 2
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03", c.COL_SDT: "0911111111", c.COL_MA_PIN: ""}])
    assert vao("NV03", "", bang=bang).user is None
    assert vao("NV01", "").user is None


def test_pin_luu_dang_so_tren_sheet_van_khop():
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03", c.COL_SDT: "0911111111", c.COL_MA_PIN: 4321}])
    assert vao("NV03", "4321", bang=bang).user is not None


def test_trung_sdt_thi_tu_choi():                              # Review Focus 3
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03"}])           # trùng SĐT với NV01
    assert vao("0912345678", "1234", bang=bang).user is None
    assert vao("NV01", "1234", bang=bang).user is not None     # vào bằng ID vẫn được


def test_khoa_sau_5_lan_sai_ke_ca_khi_dung_pin():
    g = auth.LoginGuard()
    for _ in range(4):
        vao("NV01", "0000", g)
    assert vao("NV01", "0000", g).error == c.MSG_DANG_NHAP_SAI          # lần thứ 5
    assert vao("NV01", "1234", g).error == c.MSG_TAI_KHOAN_KHOA
    assert vao("0912345678", "1234", g).error == c.MSG_TAI_KHOAN_KHOA   # cùng tài khoản, vào bằng SĐT
    assert vao("NV02", "5678", g).user is not None                      # tài khoản khác không bị ảnh hưởng


def test_het_15_phut_thi_mo_khoa():
    g = auth.LoginGuard()
    for _ in range(5):
        vao("NV01", "0000", g)
    assert vao("NV01", "1234", g, now=T0 + timedelta(minutes=14, seconds=59)).user is None
    assert vao("NV01", "1234", g, now=T0 + timedelta(minutes=15)).user is not None


def test_dang_nhap_dung_xoa_bo_dem():
    g = auth.LoginGuard()
    for _ in range(4):
        vao("NV01", "0000", g)
    vao("NV01", "1234", g)
    for _ in range(4):
        vao("NV01", "0000", g)
    assert vao("NV01", "1234", g).user is not None


def test_id_khong_ton_tai_cung_bi_khoa_de_khong_lo_id_nao_co_that():
    g = auth.LoginGuard()
    for _ in range(5):
        vao("NV99", "0000", g)
    assert vao("NV99", "0000", g).error == c.MSG_TAI_KHOAN_KHOA


def test_pin_co_ky_tu_khong_phai_ascii_khong_lam_sap():
    assert vao("NV01", "mậtkhẩu").user is None
