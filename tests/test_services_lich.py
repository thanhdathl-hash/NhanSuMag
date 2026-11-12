"""services.py: đẩy việc sang Google Calendar và lịch trình cá nhân (spec mục 12)."""
from datetime import date, time

import pytest

import config as c
import gcal
import services
from tests.conftest import NHAN_SU, lich, nguoi_dung
from tests.fakes import FakeCalendar, make_store

D = date(2026, 11, 12)
QL, NV1, NV2 = nguoi_dung(0), nguoi_dung(1), nguoi_dung(2)
LICH_NV1 = "nv01@group.calendar.google.com"


@pytest.fixture
def cal():
    return FakeCalendar()


# --- Đẩy việc được giao ---

def giao(store, notifier, cal, **kw):
    mac_dinh = dict(ten_viec="Báo cáo tuần", mo_ta="Gửi trước 17h", nguoi_nhan="NV01",
                    han_chot=date(2026, 12, 1), trong_so=3, today=D, calendar=cal)
    return services.create_task(store, notifier, QL, **{**mac_dinh, **kw})


def test_giao_viec_day_su_kien_ca_ngay_vao_han_chot(store, notifier, cal):
    r = giao(store, notifier, cal)
    assert r.calendar_pushed is True and len(cal.events) == 1
    e = cal.events[0]
    assert (e["calendar_id"], e["ngay"], e["gio_bat_dau"]) == (LICH_NV1, date(2026, 12, 1), None)
    assert "Báo cáo tuần" in e["summary"] and "Gửi trước 17h" in e["description"]
    assert e["ev_id"] == gcal.event_id("gv", r.task[c.COL_ID_VIEC])
    assert not e["lap"]


def test_nguoi_nhan_chua_co_lich_google_thi_bo_qua(store, notifier, cal):
    r = giao(store, notifier, cal, nguoi_nhan="NV02")
    assert r.calendar_pushed is None and cal.events == [] and len(store.tasks()) == 1


def test_google_loi_van_luu_viec_va_van_gui_telegram(store, notifier, cal):
    cal.ok = False
    r = giao(store, notifier, cal)
    assert r.calendar_pushed is False and r.notified is True and len(store.tasks()) == 1


def test_khong_truyen_lich_thi_khong_day(store, notifier):
    assert giao(store, notifier, None).calendar_pushed is None


def test_dau_vao_sai_thi_khong_day(store, notifier, cal):
    with pytest.raises(services.InvalidInput):
        giao(store, notifier, cal, ten_viec=" ")
    assert cal.events == []


# --- Thêm lịch trình cá nhân ---

def them(store, cal, user=NV1, **kw):
    mac_dinh = dict(noi_dung="Họp giao ban", ngay=date(2026, 11, 16))
    return services.add_personal(store, cal, user, **{**mac_dinh, **kw})


def test_them_muc_ca_ngay_khong_lap(store, cal):
    r = them(store, cal, noi_dung="  Nộp tiền điện ")
    m = store.personal().iloc[0]
    assert m[c.COL_ID_LICH].startswith("L-") and len(m[c.COL_ID_LICH]) == 10 and r.task[c.COL_ID_LICH] == m[c.COL_ID_LICH]
    assert (m[c.COL_ID_NV], m[c.COL_NOI_DUNG], m[c.COL_NGAY]) == ("NV01", "Nộp tiền điện", "2026-11-16")
    assert (m[c.COL_GIO_BAT_DAU], m[c.COL_GIO_KET_THUC], m[c.COL_LAP], m[c.COL_LAP_DEN], m[c.COL_DA_XONG]) == ("", "", c.LAP_KHONG, "", "")


def test_them_muc_co_gio_va_lap_hang_tuan_day_sang_google(store, cal):
    r = them(store, cal, gio_bat_dau=time(8, 30), gio_ket_thuc=time(9, 0), lap=c.LAP_TUAN, lap_den=date(2026, 12, 31))
    m = store.personal().iloc[0]
    assert (m[c.COL_GIO_BAT_DAU], m[c.COL_GIO_KET_THUC], m[c.COL_LAP], m[c.COL_LAP_DEN]) == ("08:30", "09:00", c.LAP_TUAN, "2026-12-31")
    e = cal.events[0]
    assert r.calendar_pushed is True and e["calendar_id"] == LICH_NV1 and e["summary"] == "Họp giao ban"
    assert (e["ngay"], e["gio_bat_dau"], e["gio_ket_thuc"], e["lap"], e["lap_den"]) == \
        (date(2026, 11, 16), time(8, 30), time(9, 0), c.LAP_TUAN, date(2026, 12, 31))
    assert e["ev_id"] == gcal.event_id("cn", m[c.COL_ID_LICH])


def test_quan_ly_cung_co_lich_ca_nhan(store, cal):
    them(store, cal, user=QL)
    assert store.personal().iloc[0][c.COL_ID_NV] == "QL01" and cal.events[0]["calendar_id"].startswith("ql01@")


def test_nguoi_chua_co_lich_google_van_them_duoc(store, cal):
    r = them(store, cal, user=NV2)
    assert r.calendar_pushed is None and cal.events == [] and len(store.personal()) == 1


def test_google_loi_van_luu_muc(store, cal):
    cal.ok = False
    assert them(store, cal).calendar_pushed is False and len(store.personal()) == 1


@pytest.mark.parametrize("kw", [
    {"noi_dung": "  "}, {"noi_dung": "x" * 201}, {"ngay": None}, {"ngay": "2026-11-16"},
    {"gio_ket_thuc": time(9, 0)},                                         # có giờ kết thúc mà thiếu giờ bắt đầu
    {"gio_bat_dau": time(9, 0), "gio_ket_thuc": time(9, 0)},             # kết thúc không sau bắt đầu
    {"gio_bat_dau": time(9, 0), "gio_ket_thuc": time(8, 0)},
    {"gio_bat_dau": "08:30"},
    {"lap": "Hằng tháng"}, {"lap": None},
    {"lap": c.LAP_NGAY},                                                  # lặp mà thiếu ngày kết thúc
    {"lap": c.LAP_NGAY, "lap_den": date(2026, 11, 15)},                   # kết thúc trước ngày đầu
    {"lap": c.LAP_TUAN, "lap_den": date(2027, 11, 18)},                   # dài hơn 366 ngày
])
def test_dau_vao_sai_bi_tu_choi_va_khong_ghi(store, cal, kw):
    with pytest.raises(services.InvalidInput):
        them(store, cal, **kw)
    assert len(store.personal()) == 0 and cal.events == []


def test_khong_lap_thi_bo_qua_ngay_ket_thuc(store, cal):
    them(store, cal, lap=c.LAP_KHONG, lap_den=date(2026, 12, 31))
    assert store.personal().iloc[0][c.COL_LAP_DEN] == "" and not cal.events[0]["lap_den"]


def test_vai_tro_la_khong_them_duoc(store, cal):
    with pytest.raises(services.PermissionDenied):
        them(store, cal, user={c.COL_ID_NV: "X", c.COL_ROLE: "Khac"})


def test_noi_dung_bat_dau_bang_dau_bang_luu_nguyen_van(store, cal):
    them(store, cal, noi_dung="=HYPERLINK(1)")
    assert store.personal().iloc[0][c.COL_NOI_DUNG] == "=HYPERLINK(1)"


# --- Các lần xảy ra ---

def test_occurrences():
    tu, den = date(2026, 11, 1), date(2026, 11, 30)
    assert services.occurrences(lich(), tu, den) == [date(2026, 11, 16)]
    assert services.occurrences(lich(Ngay="2026-12-01"), tu, den) == []
    ngay = services.occurrences(lich(Lap=c.LAP_NGAY, Lap_Den="2026-11-19"), tu, den)
    assert ngay == [date(2026, 11, d) for d in (16, 17, 18, 19)]
    tuan = services.occurrences(lich(Ngay="2026-10-26", Lap=c.LAP_TUAN, Lap_Den="2026-12-31"), tu, den)
    assert tuan == [date(2026, 11, d) for d in (2, 9, 16, 23, 30)]


@pytest.mark.parametrize("ghi_de", [{"Ngay": ""}, {"Ngay": "16/11/2026"}])
def test_occurrences_ngay_hong_thi_rong(ghi_de):
    assert services.occurrences(lich(**ghi_de), date(2026, 1, 1), date(2027, 1, 1)) == []


def test_occurrences_du_lieu_lap_hong_thi_chi_con_ngay_dau():
    for ghi_de in [{"Lap": c.LAP_NGAY, "Lap_Den": ""}, {"Lap": c.LAP_NGAY, "Lap_Den": "abc"}, {"Lap": "Lạ", "Lap_Den": "2026-12-31"}]:
        assert services.occurrences(lich(**ghi_de), date(2026, 1, 1), date(2027, 12, 31)) == [date(2026, 11, 16)]


def test_occurrences_chuoi_sua_tay_qua_dai_bi_chan():
    ngay = services.occurrences(lich(Lap=c.LAP_NGAY, Lap_Den="2099-01-01"), date(2026, 1, 1), date(2099, 1, 1))
    assert len(ngay) == c.LAP_TOI_DA_NGAY + 1


def test_personal_events_xep_theo_gio_va_danh_dau_xong():
    s = make_store(NHAN_SU, personal=[
        lich(ID_Lich="L-1", Noi_Dung="Chiều", Gio_Bat_Dau="14:00"),
        lich(ID_Lich="L-2", Noi_Dung="Cả ngày"),
        lich(ID_Lich="L-3", Noi_Dung="Sáng", Gio_Bat_Dau="08:30", Lap=c.LAP_NGAY, Lap_Den="2026-11-17", Da_Xong="2026-11-17"),
        lich(ID_Lich="L-4", Noi_Dung="Tháng sau", Ngay="2026-12-02"),
    ])
    lc = services.personal_events(s.personal(), 2026, 11)
    assert sorted(lc) == [date(2026, 11, 16), date(2026, 11, 17)]
    assert [m[c.COL_NOI_DUNG] for m in lc[date(2026, 11, 16)]] == ["Cả ngày", "Sáng", "Chiều"]
    assert [(m[c.COL_NOI_DUNG], m["xong"], m["ngay_xay_ra"]) for m in lc[date(2026, 11, 17)]] == [("Sáng", True, date(2026, 11, 17))]
    assert lc[date(2026, 11, 16)][1]["xong"] is False


def test_visible_personal_chi_cua_minh_ke_ca_quan_ly():
    s = make_store(NHAN_SU, personal=[lich(), lich(ID_Lich="L-2", ID_NV="NV02"), lich(ID_Lich="L-3", ID_NV="QL01")])
    assert list(services.visible_personal(s.personal(), NV1)[c.COL_ID_LICH]) == ["L-00000001"]
    assert list(services.visible_personal(s.personal(), QL)[c.COL_ID_LICH]) == ["L-3"]
    assert len(services.visible_personal(s.personal(), {c.COL_ID_NV: "", c.COL_ROLE: "Khac"})) == 0


# --- Đánh dấu xong ---

def kho_lap():
    return make_store(NHAN_SU, personal=[lich(Lap=c.LAP_NGAY, Lap_Den="2026-11-20")])


def test_danh_dau_xong_roi_bo(cal):
    s = kho_lap()
    services.set_personal_done(s, NV1, "L-00000001", date(2026, 11, 17), True)
    services.set_personal_done(s, NV1, "L-00000001", date(2026, 11, 16), True)
    services.set_personal_done(s, NV1, "L-00000001", date(2026, 11, 16), True)       # bấm hai lần không ghi trùng
    assert s.get_personal("L-00000001")[c.COL_DA_XONG] == "2026-11-16,2026-11-17"
    services.set_personal_done(s, NV1, "L-00000001", date(2026, 11, 17), False)
    assert s.get_personal("L-00000001")[c.COL_DA_XONG] == "2026-11-16"


def test_danh_dau_ngay_khong_thuoc_chuoi_bi_tu_choi():
    s = kho_lap()
    with pytest.raises(services.InvalidInput):
        services.set_personal_done(s, NV1, "L-00000001", date(2026, 11, 21), True)
    assert s.get_personal("L-00000001")[c.COL_DA_XONG] == ""


@pytest.mark.parametrize("user", [NV2, QL])
def test_nguoi_khac_ke_ca_quan_ly_khong_danh_dau_va_khong_xoa_duoc(cal, user):
    s = kho_lap()
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.set_personal_done(s, user, "L-00000001", date(2026, 11, 16), True)
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.delete_personal(s, cal, user, "L-00000001")
    assert len(s.personal()) == 1 and s.get_personal("L-00000001")[c.COL_DA_XONG] == "" and cal.deleted == []


# --- Xóa ---

def test_xoa_muc_va_su_kien_google(cal):
    s = kho_lap()
    r = services.delete_personal(s, cal, NV1, "L-00000001")
    assert len(s.personal()) == 0 and r.calendar_pushed is True
    assert cal.deleted == [(LICH_NV1, gcal.event_id("cn", "L-00000001"))]


def test_xoa_khi_google_loi_van_xoa_trong_app(cal):
    s = kho_lap()
    cal.ok = False
    assert services.delete_personal(s, cal, NV1, "L-00000001").calendar_pushed is False and len(s.personal()) == 0


def test_xoa_hai_lan_bao_khong_tim_thay(cal):
    s = kho_lap()
    services.delete_personal(s, cal, NV1, "L-00000001")
    with pytest.raises(services.ServiceError, match="Không tìm thấy"):
        services.delete_personal(s, cal, NV1, "L-00000001")
    assert len(cal.deleted) == 1
