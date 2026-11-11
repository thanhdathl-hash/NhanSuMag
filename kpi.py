"""Công thức KPI. Chỉ gồm hàm thuần: không đọc Sheet, không đọc đồng hồ."""
from datetime import date

import pandas as pd

import config


def days_late(han_chot: date, ngay_hoan_thanh: date) -> int:
    """Số ngày trễ so với hạn chót, không nhỏ hơn 0."""
    return max(0, (ngay_hoan_thanh - han_chot).days)


def h1(days_late: int) -> float:
    """Hệ số đúng hạn: mỗi ngày trễ trừ 0,05, thấp nhất 0,5."""
    return max(config.H1_SAN, 1 - config.H1_PHAT_MOI_NGAY * days_late)


def h2(stars: int) -> float:
    """Hệ số chất lượng theo số sao 1 đến 5."""
    if stars not in config.H2_THEO_SAO:
        raise ValueError(f"Số sao phải từ 1 đến 5, nhận được {stars!r}")
    return config.H2_THEO_SAO[stars]


def task_score(trong_so: int, days_late: int, stars: int) -> float:
    """Điểm thực tế của một việc = trọng số × H1 × H2, làm tròn 2 chữ số."""
    return round(trong_so * h1(days_late) * h2(stars), 2)


def quarter_of(d: date) -> str:
    """Quý của một ngày, ví dụ 2026-Q4."""
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def month_of(d: date) -> str:
    """Tháng của một ngày, ví dụ 2026-11."""
    return f"{d.year}-{d.month:02d}"


def _so(cot: pd.Series) -> pd.Series:
    """Đổi cột chuỗi sang số. Chấp nhận dấu phẩy thập phân; ô trống hoặc hỏng coi là 0."""
    chuoi = cot.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(chuoi, errors="coerce").fillna(0)


def quarter_target(tasks: pd.DataFrame) -> float:
    """Tổng điểm mục tiêu quý (D1-A): tổng trọng số mọi việc được giao, ở bất kỳ trạng thái nào.

    `tasks` đã được lọc sẵn theo một nhân viên và một quý.
    Đây là nơi duy nhất chứa quyết định D1.
    """
    return float(_so(tasks[config.COL_TRONG_SO]).sum())


def quarter_kpi(tasks: pd.DataFrame) -> float | None:
    """KPI quý tính bằng phần trăm, làm tròn 2 chữ số. None khi chưa có việc nào."""
    muc_tieu = quarter_target(tasks)
    if muc_tieu <= 0:
        return None
    xong = tasks[tasks[config.COL_TRANG_THAI] == config.TT_HOAN_THANH]
    thuc_te = float(_so(xong[config.COL_DIEM]).sum())
    return round(thuc_te / muc_tieu * 100, 2)


def quarter_progress(tasks: pd.DataFrame) -> tuple[int, int]:
    """(số việc đã hoàn thành, tổng số việc)."""
    return int((tasks[config.COL_TRANG_THAI] == config.TT_HOAN_THANH).sum()), len(tasks)
