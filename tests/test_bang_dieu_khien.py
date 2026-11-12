"""Bảng điều khiển: thẻ số liệu, khối lượng theo nhân viên, lịch hạn chót."""
from datetime import date

import config as c
import services
import ui
from tests.conftest import NHAN_SU, viec
from tests.fakes import make_store

D = date(2026, 11, 12)


def kho():
    return make_store(NHAN_SU, tasks=[
        viec(ID_Viec="V-1", Ten_Viec="Đang làm còn hạn", Han_Chot="2026-11-20", Trang_Thai=c.TT_DANG_LAM),
        viec(ID_Viec="V-2", Ten_Viec="Mới giao hạn hôm nay", Han_Chot="2026-11-12", Trang_Thai=c.TT_MOI_GIAO),
        viec(ID_Viec="V-3", Ten_Viec="Làm lại quá hạn", Han_Chot="2026-11-10", Trang_Thai=c.TT_LAM_LAI),
        viec(ID_Viec="V-4", Ten_Viec="Chờ duyệt", Han_Chot="2026-11-10", Trang_Thai=c.TT_CHO_DUYET, Nguoi_Nhan="NV02"),
        viec(ID_Viec="V-5", Ten_Viec="Đã xong", Han_Chot="2026-11-05", Trang_Thai=c.TT_HOAN_THANH, Nguoi_Nhan="NV02"),
        viec(ID_Viec="V-6", Ten_Viec="Hạn hỏng", Han_Chot="20/11", Trang_Thai=c.TT_DANG_LAM, Nguoi_Nhan="NV02"),
        viec(ID_Viec="V-7", Ten_Viec="Tháng sau", Han_Chot="2026-12-01", Trang_Thai=c.TT_MOI_GIAO),
        viec(ID_Viec="V-8", Ten_Viec="Trạng thái lạ", Han_Chot="2026-11-15", Trang_Thai="Xong"),
    ])


# --- services ---

def test_task_group():
    assert services.task_group(c.TT_DANG_LAM, "2026-11-12", D) == c.NHOM_DANG_LAM       # đến hạn hôm nay: chưa quá hạn
    assert services.task_group(c.TT_MOI_GIAO, "2026-11-11", D) == c.NHOM_QUA_HAN
    assert services.task_group(c.TT_LAM_LAI, "abc", D) == c.NHOM_DANG_LAM               # hạn hỏng: không kết luận quá hạn
    assert services.task_group(c.TT_CHO_DUYET, "2026-01-01", D) == c.NHOM_CHO_DUYET     # đã nộp thì không còn quá hạn
    assert services.task_group(c.TT_HOAN_THANH, "2026-01-01", D) == c.NHOM_HOAN_THANH
    assert services.task_group("Xong", "2026-11-11", D) is None


def test_dashboard_counts_khong_chong_lan():
    dem = services.dashboard_counts(kho().tasks(), D)
    assert dem == {c.NHOM_DANG_LAM: 4, c.NHOM_CHO_DUYET: 1, c.NHOM_QUA_HAN: 1, c.NHOM_HOAN_THANH: 1}
    assert list(dem) == c.NHOM_VIEC


def test_dashboard_counts_bang_trong():
    assert services.dashboard_counts(make_store(NHAN_SU).tasks(), D) == {n: 0 for n in c.NHOM_VIEC}


def test_workload_table():
    s = kho()
    b = services.workload_table(s.tasks(), s.employees(), D).set_index(c.COL_ID_NV)
    assert list(b.index) == ["NV01", "NV02"]
    assert [int(b.loc["NV01", n]) for n in c.NHOM_VIEC] == [3, 0, 1, 0]
    assert [int(b.loc["NV02", n]) for n in c.NHOM_VIEC] == [1, 1, 0, 1]
    assert b.loc["NV02", c.COL_TEN] == "Lê Bình"


def test_calendar_events():
    lich = services.calendar_events(kho().tasks(), 2026, 11, D)
    assert sorted(lich) == [date(2026, 11, 5), date(2026, 11, 10), date(2026, 11, 12), date(2026, 11, 20)]
    ngay_10 = lich[date(2026, 11, 10)]
    assert [(e[c.COL_TEN_VIEC], e["nhom"]) for e in ngay_10] == [("Chờ duyệt", c.NHOM_CHO_DUYET), ("Làm lại quá hạn", c.NHOM_QUA_HAN)]
    assert ngay_10[0][c.COL_NGUOI_NHAN] == "NV02"
    assert lich[date(2026, 11, 12)][0]["nhom"] == c.NHOM_DANG_LAM


def test_calendar_events_thang_khac():
    assert list(services.calendar_events(kho().tasks(), 2026, 12, D)) == [date(2026, 12, 1)]
    assert services.calendar_events(kho().tasks(), 2026, 10, D) == {}


def test_shift_month():
    assert services.shift_month(2026, 12, 1) == (2027, 1)
    assert services.shift_month(2026, 1, -1) == (2025, 12)
    assert services.shift_month(2026, 11, -1) == (2026, 10)


# --- ui ---

def test_stat_cards_html():
    html = ui.stat_cards_html({c.NHOM_DANG_LAM: 68, c.NHOM_CHO_DUYET: 5, c.NHOM_QUA_HAN: 12, c.NHOM_HOAN_THANH: 28})
    for nhan, so in [("Đang thực hiện", "68"), ("Chờ duyệt", "5"), ("Quá hạn", "12"), ("Hoàn thành", "28")]:
        assert nhan in html and f">{so}<" in html
    assert html.count('class="gv-the ') == 4


def test_month_weeks_bat_dau_thu_hai_va_phu_kin_thang():
    tuan = ui.month_weeks(2026, 11)
    assert len(tuan) == 6 and tuan[0][0].isoformat() == "2026-10-26" and tuan[-1][-1].isoformat() == "2026-12-06"
    assert all(len(t) == 7 and t[0].weekday() == 0 for t in tuan)


def test_md_escape():
    assert ui.md_escape("[bấm](http://x) **đậm** <b>") == "\\[bấm\\]\\(http://x\\) \\*\\*đậm\\*\\* \\<b\\>"
    assert ui.md_escape("dòng 1\ndòng 2") == "dòng 1 dòng 2"
