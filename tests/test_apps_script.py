"""Apps Script không chạy được trong pytest; ở đây đối chiếu tên với config.py
và, nếu máy có Node, chạy thử hàm thuần gomViecDenHan."""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

import config as c

GS = pathlib.Path(__file__).resolve().parent.parent / "apps_script" / "nhac_viec.gs"
SRC = GS.read_text(encoding="utf-8") if GS.exists() else ""


def test_ten_bang_cot_trang_thai_khop_config():
    for chuoi in [c.SHEET_VIEC, c.SHEET_NHAN_SU, c.COL_HAN_CHOT, c.COL_TRANG_THAI, c.COL_NGUOI_NHAN,
                  c.COL_TEN_VIEC, c.COL_ID_NV, c.COL_CHAT_ID, c.TZ, *c.TT_CHUA_NOP]:
        assert f'"{chuoi}"' in SRC, chuoi


def test_khong_nhac_viec_da_nop():
    assert f'"{c.TT_CHO_DUYET}"' not in SRC and f'"{c.TT_HOAN_THANH}"' not in SRC


def test_khong_co_token_trong_ma():
    assert not re.search(r"\d{8,10}:[A-Za-z0-9_-]{30,}", SRC) and "TELEGRAM_BOT_TOKEN" in SRC


@pytest.mark.skipif(shutil.which("node") is None, reason="cần Node để chạy thử hàm thuần của Apps Script")
def test_gom_viec_den_han():
    tieu_de = c.VIEC_COLS
    def dong(ten, nguoi, han, tt):
        d = {k: "" for k in tieu_de}
        d.update({c.COL_TEN_VIEC: ten, c.COL_NGUOI_NHAN: nguoi, c.COL_HAN_CHOT: han, c.COL_TRANG_THAI: tt})
        return [d[k] for k in tieu_de]
    rows = [
        dong("A", "NV01", "2026-11-11", c.TT_MOI_GIAO),
        dong("B", "NV01", "2026-11-11", c.TT_DANG_LAM),
        dong("C", "NV02", "2026-11-11", c.TT_LAM_LAI),
        dong("D", "NV02", "2026-11-11", c.TT_CHO_DUYET),      # đã nộp: không nhắc
        dong("E", "NV02", "2026-11-11", c.TT_HOAN_THANH),
        dong("F", "NV01", "2026-11-12", c.TT_DANG_LAM),       # chưa đến hạn
        dong("G", "NV01", "2026-11-10", c.TT_DANG_LAM),       # quá hạn: ngoài phạm vi bản đầu
        dong("H", "", "2026-11-11", c.TT_DANG_LAM),           # thiếu người nhận
        dong("I", " NV01 ", " 2026-11-11 ", c.TT_DANG_LAM),   # có khoảng trắng thừa
    ]
    js = (f"const vm=require('vm'),fs=require('fs');const ctx={{}};vm.createContext(ctx);"
          f"vm.runInContext(fs.readFileSync({json.dumps(str(GS))},'utf8'),ctx);"
          f"console.log(JSON.stringify(ctx.gomViecDenHan({json.dumps(rows)},{json.dumps(tieu_de)},'2026-11-11')));")
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == {"NV01": ["A", "B", "I"], "NV02": ["C"]}
