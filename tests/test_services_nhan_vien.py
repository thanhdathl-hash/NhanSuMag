from datetime import date

import pytest

import config as c
import services
from tests.conftest import NHAN_SU, viec
from tests.fakes import make_store

D = date(2026, 11, 22)
ID = "V-00000001"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
JPG = b"\xff\xd8\xff" + b"0" * 100


def kho(trang_thai, nhan_su=NHAN_SU):
    return make_store(nhan_su, tasks=[viec(Trang_Thai=trang_thai)])


# --- Bắt đầu ---

@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_LAM_LAI])
def test_bat_dau(nv1, tu):
    s = kho(tu)
    r = services.start_task(s, nv1, ID)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM == r.task[c.COL_TRANG_THAI]


@pytest.mark.parametrize("tu", [c.TT_DANG_LAM, c.TT_CHO_DUYET, c.TT_HOAN_THANH])
def test_bat_dau_sai_trang_thai(nv1, tu):
    s = kho(tu)
    with pytest.raises(services.InvalidState):
        services.start_task(s, nv1, ID)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == tu


def test_bat_dau_viec_nguoi_khac(nv2):
    s = kho(c.TT_MOI_GIAO)
    with pytest.raises(services.PermissionDenied):
        services.start_task(s, nv2, ID)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_MOI_GIAO


def test_quan_ly_khong_bat_dau_ho(ql):
    with pytest.raises(services.PermissionDenied):
        services.start_task(kho(c.TT_MOI_GIAO), ql, ID)


def test_viec_khong_ton_tai(nv1, notifier):                 # Review Focus 4
    s = kho(c.TT_MOI_GIAO)
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.start_task(s, nv1, "V-khongco")
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.submit_task(s, notifier, nv1, "V-khongco", link="https://a.vn", today=D)


# --- Báo cáo hoàn thành ---

@pytest.mark.parametrize("tu", [c.TT_DANG_LAM, c.TT_LAM_LAI])
def test_bao_cao_bang_link(notifier, nv1, tu):
    s = kho(tu)
    r = services.submit_task(s, notifier, nv1, ID, link=" https://drive.google.com/x ", today=D)
    t = s.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_LINK], t[c.COL_NGAY_HOAN_THANH]) == \
        (c.TT_CHO_DUYET, "https://drive.google.com/x", "2026-11-22")
    assert r.notified and notifier.sent[0][0] == "100"                   # T3 tới quản lý
    assert "Nguyễn An" in notifier.sent[0][1] and "https://drive.google.com/x" in notifier.sent[0][1]


@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_CHO_DUYET, c.TT_HOAN_THANH])
def test_bao_cao_sai_trang_thai(notifier, nv1, tu):          # bấm hai lần rơi vào ca Chờ duyệt
    s = kho(tu)
    with pytest.raises(services.InvalidState):
        services.submit_task(s, notifier, nv1, ID, link="https://a.vn", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == tu and notifier.sent == []


@pytest.mark.parametrize("kw", [
    {}, {"link": ""}, {"link": "   "}, {"link": "drive.google.com/x"}, {"link": "javascript:alert(1)"},
    {"link": "https://a.vn có khoảng trắng"}, {"link": "tg:FILE999"},
    {"link": "https://a.vn", "photo": PNG}, {"photo": b""}, {"photo": b"khong phai anh"},
    {"photo": PNG + b"0" * c.ANH_MAX_BYTES},
])
def test_chung_minh_khong_hop_le(notifier, nv1, kw):
    s = kho(c.TT_DANG_LAM)
    with pytest.raises(services.InvalidInput):
        services.submit_task(s, notifier, nv1, ID, today=D, **kw)
    t = s.get_task(ID)
    assert t[c.COL_TRANG_THAI] == c.TT_DANG_LAM and t[c.COL_LINK] == "" and notifier.sent == []


def test_bao_cao_viec_nguoi_khac(notifier, nv2):
    s = kho(c.TT_DANG_LAM)
    with pytest.raises(services.PermissionDenied):
        services.submit_task(s, notifier, nv2, ID, link="https://a.vn", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM


def test_quan_ly_khong_bao_cao_ho(notifier, ql):
    with pytest.raises(services.PermissionDenied):
        services.submit_task(kho(c.TT_DANG_LAM), notifier, ql, ID, link="https://a.vn", today=D)


def test_bao_cao_link_telegram_loi_van_luu(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    notifier.ok = False
    r = services.submit_task(s, notifier, nv1, ID, link="https://a.vn", today=D)
    assert r.notified is False and s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


@pytest.mark.parametrize("anh, ten", [(PNG, "a.png"), (JPG, "a.jpg")])
def test_bao_cao_bang_anh(notifier, nv1, anh, ten):
    s = kho(c.TT_DANG_LAM)
    r = services.submit_task(s, notifier, nv1, ID, photo=anh, photo_name=ten, today=D)
    t = s.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_LINK], t[c.COL_NGAY_HOAN_THANH]) == (c.TT_CHO_DUYET, "tg:FILE123", "2026-11-22")
    assert r.notified is True
    assert notifier.sent[0][0] == "100" and len(notifier.sent) == 1       # ảnh chính là T3, không gửi thêm tin
    assert "Nguyễn An" in notifier.sent[0][1]


def test_anh_gui_loi_thi_khong_chuyen_trang_thai(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    notifier.ok = False
    with pytest.raises(services.ServiceError, match="link"):
        services.submit_task(s, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and s.get_task(ID)[c.COL_LINK] == ""


def test_quan_ly_chua_co_chat_id_thi_tu_choi_anh(notifier, nv1):
    s = kho(c.TT_DANG_LAM, [{**NHAN_SU[0], c.COL_CHAT_ID: ""}] + NHAN_SU[1:])
    with pytest.raises(services.ServiceError, match="link"):
        services.submit_task(s, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and notifier.sent == []


def test_thieu_quan_ly_thi_bao_cao_link_van_luu(notifier, nv1):          # Review Focus 4
    s = kho(c.TT_DANG_LAM, NHAN_SU[1:])
    r = services.submit_task(s, notifier, nv1, ID, link="https://a.vn", today=D)
    assert r.notified is False and s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
