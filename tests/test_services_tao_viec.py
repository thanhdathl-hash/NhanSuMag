import re
from datetime import date, datetime, timezone

import pytest

import config as c
import services
from tests.conftest import NHAN_SU, viec
from tests.fakes import make_store

D = date(2026, 11, 11)


def tao(store, notifier, user, **kw):
    mac_dinh = dict(ten_viec="Báo cáo tuần", mo_ta="", nguoi_nhan="NV01",
                    han_chot=date(2026, 12, 1), trong_so=3, today=D)
    return services.create_task(store, notifier, user, **{**mac_dinh, **kw})


def test_tao_viec_ghi_du_cot(store, notifier, ql):
    r = tao(store, notifier, ql, ten_viec="  Báo cáo tuần ", mo_ta=" Gửi trước 17h ")
    t = store.tasks().iloc[0]
    assert re.fullmatch(r"V-[0-9a-f]{8}", t[c.COL_ID_VIEC]) and r.task[c.COL_ID_VIEC] == t[c.COL_ID_VIEC]
    assert (t[c.COL_TEN_VIEC], t[c.COL_MO_TA], t[c.COL_NGUOI_NHAN]) == ("Báo cáo tuần", "Gửi trước 17h", "NV01")
    assert (t[c.COL_TRANG_THAI], t[c.COL_NGAY_GIAO], t[c.COL_HAN_CHOT]) == (c.TT_MOI_GIAO, "2026-11-11", "2026-12-01")
    assert (t[c.COL_THANG], t[c.COL_QUY], t[c.COL_TRONG_SO]) == ("2026-12", "2026-Q4", "3")
    assert t[c.COL_LINK] == t[c.COL_SAO] == t[c.COL_DIEM] == t[c.COL_NGAY_HOAN_THANH] == t[c.COL_GHI_CHU_QL] == ""


def test_quy_theo_han_chot_khong_theo_ngay_giao(store, notifier, ql):
    assert tao(store, notifier, ql, han_chot=date(2027, 1, 5)).task[c.COL_QUY] == "2027-Q1"


def test_t1_gui_cho_nguoi_nhan(store, notifier, ql):
    assert tao(store, notifier, ql).notified is True
    assert notifier.sent[0][0] == "201" and "Báo cáo tuần" in notifier.sent[0][1]


def test_telegram_loi_van_luu(store, notifier, ql):
    notifier.ok = False
    assert tao(store, notifier, ql).notified is False and len(store.tasks()) == 1


def test_nguoi_nhan_chua_co_chat_id_van_luu(store, notifier, ql):          # Review Focus 5
    assert tao(store, notifier, ql, nguoi_nhan="NV02").notified is False and len(store.tasks()) == 1


def test_nhan_vien_khong_duoc_tao(store, notifier, nv1):
    with pytest.raises(services.PermissionDenied):
        tao(store, notifier, nv1)
    assert len(store.tasks()) == 0


@pytest.mark.parametrize("kw", [{"ten_viec": "  "}, {"trong_so": 0}, {"trong_so": 6}, {"trong_so": 2.5},
                                {"trong_so": True}, {"trong_so": None},
                                {"nguoi_nhan": "NV99"}, {"nguoi_nhan": "QL01"}, {"nguoi_nhan": ""},
                                {"han_chot": None}, {"han_chot": "2026-12-01"}])
def test_dau_vao_sai_bi_tu_choi_va_khong_ghi(store, notifier, ql, kw):
    with pytest.raises(services.InvalidInput):
        tao(store, notifier, ql, **kw)
    assert len(store.tasks()) == 0 and notifier.sent == []


def test_id_trung_thi_sinh_lai(store, notifier, ql, monkeypatch):
    it = iter(["aaaaaaaa", "aaaaaaaa", "bbbbbbbb"])
    monkeypatch.setattr(services.secrets, "token_hex", lambda n: next(it))
    tao(store, notifier, ql)
    tao(store, notifier, ql, ten_viec="Việc thứ hai")
    assert list(store.tasks()[c.COL_ID_VIEC]) == ["V-aaaaaaaa", "V-bbbbbbbb"]


def test_visible_tasks(store, ql, nv1, nv2):
    store.append_task(viec())
    store.append_task(viec(ID_Viec="V-00000002", Nguoi_Nhan="NV02"))
    assert len(services.visible_tasks(store.tasks(), ql)) == 2
    assert list(services.visible_tasks(store.tasks(), nv1)[c.COL_ID_VIEC]) == ["V-00000001"]
    assert list(services.visible_tasks(store.tasks(), nv2)[c.COL_ID_VIEC]) == ["V-00000002"]


def test_visible_tasks_vai_tro_la_thi_khong_thay_gi(store):
    store.append_task(viec())
    la = {c.COL_ID_NV: "X", c.COL_ROLE: "Khac"}
    assert len(services.visible_tasks(store.tasks(), la)) == 0


def test_hom_nay_theo_gio_viet_nam(monkeypatch):
    # 2026-11-10 18:30 UTC = 2026-11-11 01:30 giờ Việt Nam
    monkeypatch.setattr(services, "_now_utc", lambda: datetime(2026, 11, 10, 18, 30, tzinfo=timezone.utc))
    assert services.hom_nay() == date(2026, 11, 11)


def test_find_manager(store):
    assert services.find_manager(store.employees())[c.COL_ID_NV] == "QL01"


def test_find_manager_can_dung_mot_quan_ly():                               # Review Focus 4
    with pytest.raises(services.ServiceError):
        services.find_manager(make_store(NHAN_SU[1:]).employees())
    with pytest.raises(services.ServiceError):
        services.find_manager(make_store(NHAN_SU + [{**NHAN_SU[0], c.COL_ID_NV: "QL02"}]).employees())
