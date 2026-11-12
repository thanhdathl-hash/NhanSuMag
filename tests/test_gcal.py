"""gcal.py với phiên HTTP giả: không gọi Google thật."""
from datetime import date, time
from types import SimpleNamespace

import pytest
import requests

import config as c
import gcal

LICH = "nv01@group.calendar.google.com"
URL = "https://www.googleapis.com/calendar/v3/calendars/nv01%40group.calendar.google.com/events"


class PhienGia:
    def __init__(self, ma=200, loi=None):
        self.ma, self.loi, self.calls = ma, loi, []

    def _goi(self, kieu, url, **kw):
        self.calls.append(SimpleNamespace(kieu=kieu, url=url, kw=kw))
        if self.loi:
            raise self.loi
        return SimpleNamespace(status_code=self.ma)

    def post(self, url, **kw):
        return self._goi("post", url, **kw)

    def delete(self, url, **kw):
        return self._goi("delete", url, **kw)


def test_event_id_hop_le_va_on_dinh():
    a = gcal.event_id("gv", "V-ab12cd34")
    assert a == gcal.event_id("gv", "V-ab12cd34") != gcal.event_id("gv", "V-ab12cd35")
    assert a != gcal.event_id("cn", "V-ab12cd34")
    for ma in ["V-ab12cd34", "Mã có dấu & KÝ TỰ lạ", ""]:
        e = gcal.event_id("gv", ma)
        assert 5 <= len(e) <= 64 and set(e) <= set("0123456789abcdefghijklmnopqrstuv")


def test_su_kien_ca_ngay():
    p = PhienGia()
    ok = gcal.GoogleCalendar(p).add_event(LICH, "gvabc", "Báo cáo tuần", "Mô tả", date(2026, 11, 30))
    goi = p.calls[0]
    assert ok is True and goi.kieu == "post" and goi.url == URL and goi.kw["timeout"] == 10
    assert goi.kw["json"] == {"id": "gvabc", "summary": "Báo cáo tuần", "description": "Mô tả",
                              "start": {"date": "2026-11-30"}, "end": {"date": "2026-12-01"}}


def test_su_kien_co_gio():
    p = PhienGia()
    gcal.GoogleCalendar(p).add_event(LICH, "cnabc", "Họp", "", date(2026, 11, 16), time(8, 30), time(9, 15))
    body = p.calls[0].kw["json"]
    assert body["start"] == {"dateTime": "2026-11-16T08:30:00", "timeZone": c.TZ}
    assert body["end"] == {"dateTime": "2026-11-16T09:15:00", "timeZone": c.TZ}


def test_co_gio_bat_dau_khong_co_gio_ket_thuc_thi_dai_mot_tieng():
    p = PhienGia()
    gcal.GoogleCalendar(p).add_event(LICH, "cnabc", "Họp", "", date(2026, 11, 16), time(23, 30))
    assert p.calls[0].kw["json"]["end"] == {"dateTime": "2026-11-17T00:30:00", "timeZone": c.TZ}


@pytest.mark.parametrize("lap, gio, rrule", [
    (c.LAP_NGAY, None, "RRULE:FREQ=DAILY;UNTIL=20261231"),
    (c.LAP_TUAN, None, "RRULE:FREQ=WEEKLY;UNTIL=20261231"),
    (c.LAP_TUAN, time(8, 30), "RRULE:FREQ=WEEKLY;UNTIL=20261231T165959Z"),     # hết ngày 31/12 giờ Việt Nam, đổi sang UTC
])
def test_lap(lap, gio, rrule):
    p = PhienGia()
    gcal.GoogleCalendar(p).add_event(LICH, "cnabc", "Họp", "", date(2026, 11, 16), gio, None, lap, date(2026, 12, 31))
    assert p.calls[0].kw["json"]["recurrence"] == [rrule]


def test_khong_lap_thi_khong_co_recurrence():
    p = PhienGia()
    gcal.GoogleCalendar(p).add_event(LICH, "cnabc", "Họp", "", date(2026, 11, 16), None, None, c.LAP_KHONG, None)
    assert "recurrence" not in p.calls[0].kw["json"]


def test_da_ton_tai_thi_coi_la_thanh_cong():
    assert gcal.GoogleCalendar(PhienGia(409)).add_event(LICH, "gvabc", "A", "", date(2026, 11, 30)) is True


@pytest.mark.parametrize("ma", [400, 403, 404, 500])
def test_google_tu_choi_tra_false(ma):
    assert gcal.GoogleCalendar(PhienGia(ma)).add_event(LICH, "gvabc", "A", "", date(2026, 11, 30)) is False
    assert gcal.GoogleCalendar(PhienGia(ma if ma != 404 else 500)).delete_event(LICH, "gvabc") is False


@pytest.mark.parametrize("loi", [requests.ConnectionError("x"), requests.Timeout("x"), ValueError("x")])
def test_loi_mang_khong_nem(loi):
    import google.auth.exceptions
    for e in (loi, google.auth.exceptions.RefreshError("x")):
        assert gcal.GoogleCalendar(PhienGia(loi=e)).add_event(LICH, "gvabc", "A", "", date(2026, 11, 30)) is False
        assert gcal.GoogleCalendar(PhienGia(loi=e)).delete_event(LICH, "gvabc") is False


@pytest.mark.parametrize("lich", ["", "   ", None])
def test_thieu_ma_lich_khong_goi_mang(lich):
    p = PhienGia()
    assert gcal.GoogleCalendar(p).add_event(lich, "gvabc", "A", "", date(2026, 11, 30)) is False
    assert gcal.GoogleCalendar(p).delete_event(lich, "gvabc") is False and p.calls == []


def test_khong_co_phien_thi_tra_false():
    assert gcal.GoogleCalendar(None).add_event(LICH, "gvabc", "A", "", date(2026, 11, 30)) is False
    assert gcal.GoogleCalendar(None).delete_event(LICH, "gvabc") is False


def test_xoa():
    p = PhienGia(204)
    assert gcal.GoogleCalendar(p).delete_event(LICH, "cnabc") is True
    assert p.calls[0].kieu == "delete" and p.calls[0].url == URL + "/cnabc" and p.calls[0].kw["timeout"] == 10


@pytest.mark.parametrize("ma", [404, 410])
def test_xoa_su_kien_da_mat_thi_coi_la_thanh_cong(ma):
    assert gcal.GoogleCalendar(PhienGia(ma)).delete_event(LICH, "cnabc") is True


@pytest.mark.parametrize("secrets", [{}, {"gcp_service_account": {"type": "service_account"}}, {"gcp_service_account": "sai"}])
def test_from_secrets_sai_thi_app_van_chay(secrets):
    lich = gcal.from_secrets(secrets)
    assert lich.add_event(LICH, "gvabc", "A", "", date(2026, 11, 30)) is False


def test_tom_tat_dai_duoc_cat():
    p = PhienGia()
    gcal.GoogleCalendar(p).add_event(LICH, "gvabc", "A" * 2000, "B" * 10000, date(2026, 11, 30))
    body = p.calls[0].kw["json"]
    assert len(body["summary"]) == 1024 and len(body["description"]) == 8000
