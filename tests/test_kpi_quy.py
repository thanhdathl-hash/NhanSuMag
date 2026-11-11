import pandas as pd

import config as c
import kpi


def bang(*dong):  # mỗi dòng: (trong_so, trang_thai, diem), đều là chuỗi
    return pd.DataFrame(
        [{c.COL_TRONG_SO: t, c.COL_TRANG_THAI: s, c.COL_DIEM: d} for t, s, d in dong],
        columns=[c.COL_TRONG_SO, c.COL_TRANG_THAI, c.COL_DIEM],
    )


def test_vi_du_spec_49_57():
    df = bang(("3", c.TT_HOAN_THANH, "3.24"), ("5", c.TT_HOAN_THANH, "2.5"),
              ("2", c.TT_HOAN_THANH, "1.2"), ("4", c.TT_DANG_LAM, ""))
    assert kpi.quarter_target(df) == 14
    assert kpi.quarter_kpi(df) == 49.57
    assert kpi.quarter_progress(df) == (3, 4)


def test_chua_co_viec_tra_none():
    assert kpi.quarter_kpi(bang()) is None
    assert kpi.quarter_progress(bang()) == (0, 0)


def test_cao_nhat_120():
    assert kpi.quarter_kpi(bang(("5", c.TT_HOAN_THANH, "6.0"), ("1", c.TT_HOAN_THANH, "1.2"))) == 120.0


def test_diem_cua_viec_chua_hoan_thanh_khong_duoc_tinh():   # ô điểm còn sót sau khi sửa tay
    assert kpi.quarter_kpi(bang(("4", c.TT_LAM_LAI, "4.0"), ("4", c.TT_HOAN_THANH, "4.0"))) == 50.0


def test_o_hong_coi_la_0():                                  # Review Focus 1
    df = bang(("", c.TT_MOI_GIAO, ""), ("abc", c.TT_DANG_LAM, ""), ("2", c.TT_HOAN_THANH, "x"),
              ("2", c.TT_HOAN_THANH, "2,4"))
    assert kpi.quarter_target(df) == 4
    assert kpi.quarter_kpi(df) == 60.0       # "2,4" đọc là 2.4; "x" là 0
