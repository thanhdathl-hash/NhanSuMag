"""Giữ quy ước: tên bảng, cột, trạng thái chỉ khai báo trong config.py."""
import pathlib
import re

import config

MODULES = ["kpi.py", "db.py", "auth.py", "notifier.py", "services.py", "app.py", "ui.py", "demo.py"]
CAM = config.TRANG_THAI + config.VIEC_COLS + config.NHAN_SU_COLS + config.MAU_COLS + list(config.SHEET_COLS)


def test_khong_viet_ten_cot_trang_thai_ngoai_config():
    for ten in MODULES:
        p = pathlib.Path(ten)
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        for chuoi in CAM:
            assert f'"{chuoi}"' not in src and f"'{chuoi}'" not in src, f"{ten} viết thẳng {chuoi!r}"


def test_khong_dung_date_today():
    for ten in MODULES:
        p = pathlib.Path(ten)
        if p.exists():
            assert not re.search(r"date\.today\(|datetime\.today\(", p.read_text(encoding="utf-8")), ten
