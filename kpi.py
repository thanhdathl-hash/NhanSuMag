"""Công thức KPI. Chỉ gồm hàm thuần: không đọc Sheet, không đọc đồng hồ."""
from datetime import date

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
