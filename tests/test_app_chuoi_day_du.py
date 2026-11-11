from datetime import date

import config as c
from tests.conftest import dang_nhap, mo_app


def test_dang_nhap_giao_bat_dau_bao_cao_duyet(app_env):
    store, notifier = app_env()                              # ban đầu không có việc
    at = dang_nhap(mo_app(), "QL01", "1111")
    at.text_input(key="gv_ten").set_value("Báo cáo tuần")
    at.number_input(key="gv_trong_so").set_value(3)
    at.selectbox(key="gv_nguoi_nhan").set_value("NV01")
    at.date_input(key="gv_han_chot").set_value(date(2026, 11, 20))
    at.button(key="gv_submit").click().run()
    id_viec = store.tasks().iloc[0][c.COL_ID_VIEC]
    at.button(key="logout").click().run()

    dang_nhap(at, "0912345678", "1234")
    at.button(key=f"start_{id_viec}").click().run()
    at.text_input(key=f"link_{id_viec}").set_value("https://a.vn")
    at.button(key=f"nop_{id_viec}").click().run()
    at.button(key="logout").click().run()

    dang_nhap(at, "QL01", "1111")
    at.radio(key=f"sao_{id_viec}").set_value(5)
    at.button(key=f"duyet_{id_viec}").click().run()

    t = store.get_task(id_viec)
    assert (t[c.COL_TRANG_THAI], t[c.COL_DIEM]) == (c.TT_HOAN_THANH, "3.6")      # đúng hạn, 5 sao: 3 × 1,0 × 1,2
    assert store.employees().iloc[1][c.COL_KPI_QUY] == "120.0"
    assert [m[0] for m in notifier.sent] == ["201", "100", "201"]                # T1, T3, T4
    assert not at.exception
