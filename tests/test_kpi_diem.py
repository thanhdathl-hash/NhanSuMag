from datetime import date

import pytest

import kpi


@pytest.mark.parametrize("trong_so, tre, sao, h1, h2, diem", [
    (3, 0, 4, 1.00, 1.0, 3.00), (1, 0, 5, 1.00, 1.2, 1.20), (3, 2, 5, 0.90, 1.2, 3.24),
    (4, 1, 3, 0.95, 0.8, 3.04), (4, 9, 2, 0.55, 0.7, 1.54), (5, 10, 4, 0.50, 1.0, 2.50),
    (5, 30, 4, 0.50, 1.0, 2.50), (2, 0, 1, 1.00, 0.6, 1.20),
])
def test_bang_ca_spec_muc_7(trong_so, tre, sao, h1, h2, diem):
    assert kpi.h1(tre) == pytest.approx(h1)
    assert kpi.h2(sao) == h2
    assert kpi.task_score(trong_so, tre, sao) == diem


def test_days_late():
    assert kpi.days_late(date(2026, 11, 10), date(2026, 11, 12)) == 2
    assert kpi.days_late(date(2026, 11, 10), date(2026, 11, 7)) == 0    # xong sớm 3 ngày
    assert kpi.days_late(date(2026, 12, 31), date(2027, 1, 2)) == 2     # qua năm


@pytest.mark.parametrize("sao", [0, 6, -1])
def test_h2_sao_ngoai_khoang(sao):
    with pytest.raises(ValueError):
        kpi.h2(sao)


@pytest.mark.parametrize("d, quy, thang", [
    (date(2026, 1, 1), "2026-Q1", "2026-01"), (date(2026, 3, 31), "2026-Q1", "2026-03"),
    (date(2026, 4, 1), "2026-Q2", "2026-04"), (date(2026, 9, 30), "2026-Q3", "2026-09"),
    (date(2026, 10, 1), "2026-Q4", "2026-10"), (date(2026, 12, 31), "2026-Q4", "2026-12"),
])
def test_quy_va_thang(d, quy, thang):
    assert kpi.quarter_of(d) == quy and kpi.month_of(d) == thang
