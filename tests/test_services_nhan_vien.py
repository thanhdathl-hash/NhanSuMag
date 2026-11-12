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
        services.submit_task(s, notifier, nv1, "V-khongco", today=D)


# --- Báo cáo hoàn thành ---

@pytest.mark.parametrize("tu", [c.TT_DANG_LAM, c.TT_LAM_LAI])
def test_bao_cao_khong_can_chung_minh(notifier, nv1, tu):
    s = kho(tu)
    r = services.submit_task(s, notifier, nv1, ID, today=D)
    t = s.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_LINK], t[c.COL_GHI_CHU_NV], t[c.COL_NGAY_HOAN_THANH]) == \
        (c.TT_CHO_DUYET, "", "", "2026-11-22")
    assert r.notified and notifier.sent[0][0] == "100" and "Nguyễn An" in notifier.sent[0][1]   # T3 tới quản lý


def test_bao_cao_kem_ghi_chu(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    services.submit_task(s, notifier, nv1, ID, ghi_chu="  Đã gọi 10 khách, 3 khách đặt hàng ", today=D)
    assert s.get_task(ID)[c.COL_GHI_CHU_NV] == "Đã gọi 10 khách, 3 khách đặt hàng"
    assert "Đã gọi 10 khách, 3 khách đặt hàng" in notifier.sent[0][1]


def test_ghi_chu_qua_dai_bi_tu_choi(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    with pytest.raises(services.InvalidInput):
        services.submit_task(s, notifier, nv1, ID, ghi_chu="x" * (c.GHI_CHU_NV_TOI_DA + 1), today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and notifier.sent == []


def test_khong_con_nhan_link():
    import inspect
    assert "link" not in inspect.signature(services.submit_task).parameters


@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_CHO_DUYET, c.TT_HOAN_THANH])
def test_bao_cao_sai_trang_thai(notifier, nv1, tu):          # bấm hai lần rơi vào ca Chờ duyệt
    s = kho(tu)
    with pytest.raises(services.InvalidState):
        services.submit_task(s, notifier, nv1, ID, today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == tu and notifier.sent == []


@pytest.mark.parametrize("anh", [b"", b"khong phai anh", PNG + b"0" * c.ANH_MAX_BYTES])
def test_anh_khong_hop_le(notifier, nv1, anh):
    s = kho(c.TT_DANG_LAM)
    with pytest.raises(services.InvalidInput):
        services.submit_task(s, notifier, nv1, ID, photo=anh, photo_name="a.png", today=D)
    t = s.get_task(ID)
    assert t[c.COL_TRANG_THAI] == c.TT_DANG_LAM and t[c.COL_LINK] == "" and notifier.sent == []


def test_bao_cao_viec_nguoi_khac(notifier, nv2):
    s = kho(c.TT_DANG_LAM)
    with pytest.raises(services.PermissionDenied):
        services.submit_task(s, notifier, nv2, ID, today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM


def test_quan_ly_khong_bao_cao_ho(notifier, ql):
    with pytest.raises(services.PermissionDenied):
        services.submit_task(kho(c.TT_DANG_LAM), notifier, ql, ID, today=D)


def test_bao_cao_telegram_loi_van_luu(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    notifier.ok = False
    r = services.submit_task(s, notifier, nv1, ID, today=D)
    assert r.notified is False and s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


@pytest.mark.parametrize("anh, ten", [(PNG, "a.png"), (JPG, "a.jpg")])
def test_bao_cao_bang_anh(notifier, nv1, anh, ten):
    s = kho(c.TT_DANG_LAM)
    r = services.submit_task(s, notifier, nv1, ID, photo=anh, photo_name=ten, ghi_chu="Kệ đã xếp xong", today=D)
    t = s.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_LINK], t[c.COL_GHI_CHU_NV], t[c.COL_NGAY_HOAN_THANH]) == \
        (c.TT_CHO_DUYET, "tg:FILE123", "Kệ đã xếp xong", "2026-11-22")
    assert r.notified is True
    assert notifier.sent[0][0] == "100" and len(notifier.sent) == 1       # ảnh chính là T3, không gửi thêm tin
    assert "Nguyễn An" in notifier.sent[0][1] and "Kệ đã xếp xong" in notifier.sent[0][1]


def test_anh_gui_loi_thi_khong_chuyen_trang_thai(notifier, nv1):
    s = kho(c.TT_DANG_LAM)
    notifier.ok = False
    with pytest.raises(services.ServiceError, match="không kèm ảnh"):
        services.submit_task(s, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and s.get_task(ID)[c.COL_LINK] == ""


def test_quan_ly_chua_co_chat_id_thi_tu_choi_anh(notifier, nv1):
    s = kho(c.TT_DANG_LAM, [{**NHAN_SU[0], c.COL_CHAT_ID: ""}] + NHAN_SU[1:])
    with pytest.raises(services.ServiceError, match="không kèm ảnh"):
        services.submit_task(s, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and notifier.sent == []


def test_nop_lai_khong_anh_thi_xoa_anh_cu(notifier, nv1):
    s = make_store(NHAN_SU, tasks=[viec(Trang_Thai=c.TT_LAM_LAI, Link_Chung_Minh="tg:CU", Ghi_Chu_NV="cũ")])
    services.submit_task(s, notifier, nv1, ID, today=D)
    t = s.get_task(ID)
    assert t[c.COL_LINK] == "" and t[c.COL_GHI_CHU_NV] == ""             # chỉ giữ báo cáo lần cuối


def test_thieu_quan_ly_thi_bao_cao_van_luu(notifier, nv1):          # Review Focus 4
    s = kho(c.TT_DANG_LAM, NHAN_SU[1:])
    r = services.submit_task(s, notifier, nv1, ID, today=D)
    assert r.notified is False and s.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
