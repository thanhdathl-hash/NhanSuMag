"""Chế độ chạy thử: xem app với dữ liệu mẫu, không cần Google Sheet, service account hay bot Telegram.

    streamlit run demo.py

Dữ liệu nằm trong bộ nhớ, dùng chung cho mọi tab trình duyệt và mất khi tắt app.
Tin Telegram không được gửi đi đâu cả; chúng hiện ở thanh bên để bạn thấy app sẽ nhắn gì.
File này KHÔNG dùng để triển khai. App thật vẫn là app.py.
"""
import io
import pathlib
import runpy
from datetime import timedelta

import streamlit as st

import config as c
import db
import kpi
import notifier
import services
from tests.fakes import FakeSpreadsheet, FakeWorksheet

APP = str(pathlib.Path(__file__).resolve().parent / "app.py")
ANH_MAU = "DEMO1"

NHAN_SU = [
    ("QL01", "Trần Quản Lý", "0900000001", "1111", c.ROLE_QUAN_LY),
    ("NV01", "Nguyễn An", "0912345671", "1234", c.ROLE_NHAN_VIEN),
    ("NV02", "Lê Bình", "0912345672", "1234", c.ROLE_NHAN_VIEN),
    ("NV03", "Phạm Chi", "0912345673", "1234", c.ROLE_NHAN_VIEN),
    ("NV04", "Hoàng Dũng", "0912345674", "1234", c.ROLE_NHAN_VIEN),
    ("NV05", "Vũ Hạnh", "0912345675", "1234", c.ROLE_NHAN_VIEN),
]
MAU = [
    ("M01", "Báo cáo doanh số tuần", "Gửi file tổng hợp trước 17h thứ Sáu", 2),
    ("M02", "Kiểm kê kho", "Đếm thực tế, đối chiếu với sổ, ghi rõ chênh lệch", 4),
    ("M03", "Đăng bài fanpage", "Một bài kèm ảnh, đúng mẫu thương hiệu", 1),
]


class DemoNotifier:
    """Thay cho Telegram: ghi lại tin để hiện ở thanh bên, giữ ảnh trong bộ nhớ."""

    def __init__(self):
        self.tin = []       # (chat_id, nội dung)
        self.anh = {}       # file_id -> bytes

    def send_message(self, chat_id, text):
        if not chat_id:
            return False
        self.tin.append((chat_id, text))
        return True

    def send_photo(self, chat_id, photo, filename, caption):
        if not chat_id:
            return None
        file_id = f"DEMO{len(self.anh) + 1}"
        self.anh[file_id] = photo
        self.tin.append((chat_id, f"[Ảnh {filename}] {caption}"))
        return file_id

    def fetch_photo(self, file_id):
        return self.anh.get(file_id)


def _anh_mau() -> bytes:
    from PIL import Image, ImageDraw
    anh = Image.new("RGB", (480, 300), "#dfe9f3")
    ve = ImageDraw.Draw(anh)
    ve.rectangle([40, 60, 440, 240], outline="#4a6fa5", width=4)
    ve.text((150, 140), "ANH CHUNG MINH (MAU)", fill="#2c3e50")
    buf = io.BytesIO()
    anh.save(buf, format="PNG")
    return buf.getvalue()


def _viec_mau(hom_nay):
    def ngay(lech):
        return (hom_nay + timedelta(days=lech)).isoformat()

    dong, so = [], 0

    def them(ten, nguoi, trong_so, han, trang_thai, mo_ta="", nop=None, sao=None, link="", ghi_chu=""):
        nonlocal so
        so += 1
        han_chot = hom_nay + timedelta(days=han)
        diem = ""
        if sao is not None:
            diem = str(kpi.task_score(trong_so, max(0, nop - han), sao))
        dong.append({
            c.COL_ID_VIEC: f"V-demo{so:04d}", c.COL_TEN_VIEC: ten, c.COL_MO_TA: mo_ta, c.COL_NGUOI_NHAN: nguoi,
            c.COL_TRONG_SO: str(trong_so), c.COL_NGAY_GIAO: ngay(han - 7), c.COL_HAN_CHOT: han_chot.isoformat(),
            c.COL_TRANG_THAI: trang_thai, c.COL_LINK: link,
            c.COL_NGAY_HOAN_THANH: "" if nop is None else ngay(nop),
            c.COL_SAO: "" if sao is None else str(sao), c.COL_DIEM: diem, c.COL_GHI_CHU_QL: ghi_chu,
            c.COL_THANG: kpi.month_of(han_chot), c.COL_QUY: kpi.quarter_of(han_chot),
        })

    vi_du = "https://example.com"
    them("Báo cáo doanh số tuần", "NV01", 2, -10, c.TT_HOAN_THANH, nop=-10, sao=5, link=f"{vi_du}/bao-cao")
    them("Kiểm kê kho", "NV01", 4, -6, c.TT_HOAN_THANH, nop=-4, sao=4, link=f"{vi_du}/kiem-ke")
    them("Sửa báo giá khách A", "NV01", 3, 2, c.TT_LAM_LAI, nop=-1, link=f"{vi_du}/bao-gia",
         ghi_chu="Thiếu số liệu tháng trước")
    them("Gọi lại 10 khách hàng cũ", "NV01", 2, 5, c.TT_MOI_GIAO, mo_ta="Ghi kết quả từng cuộc gọi vào file chung")
    them("Chụp ảnh trưng bày kệ hàng", "NV02", 3, 1, c.TT_CHO_DUYET, nop=0, link=c.TG_PREFIX + ANH_MAU)
    them("Lập bảng giá mới", "NV02", 3, -3, c.TT_DANG_LAM)
    them("Soạn hợp đồng mẫu", "NV03", 5, -1, c.TT_CHO_DUYET, nop=0, link=f"{vi_du}/hop-dong")
    them("Đăng bài fanpage", "NV03", 1, -2, c.TT_HOAN_THANH, nop=-2, sao=3, link=f"{vi_du}/bai-dang")
    them("Đối chiếu công nợ", "NV04", 4, 7, c.TT_DANG_LAM)
    return dong


def _bang(cols, dong):
    return FakeWorksheet([list(cols)] + [[d.get(k, "") for k in cols] for d in dong])


@st.cache_resource
def _moi_truong():
    nhan_su = [{c.COL_ID_NV: i, c.COL_TEN: ten, c.COL_SDT: sdt, c.COL_MA_PIN: pin,
                c.COL_CHAT_ID: f"demo-{i}", c.COL_ROLE: role} for i, ten, sdt, pin, role in NHAN_SU]
    mau = [dict(zip(c.MAU_COLS, m)) for m in MAU]
    store = db.SheetStore(FakeSpreadsheet({
        c.SHEET_NHAN_SU: _bang(c.NHAN_SU_COLS, nhan_su),
        c.SHEET_MAU: _bang(c.MAU_COLS, mau),
        c.SHEET_VIEC: _bang(c.VIEC_COLS, _viec_mau(services.hom_nay())),
    }))
    gia = DemoNotifier()
    gia.anh[ANH_MAU] = _anh_mau()
    return store, gia


store, telegram_gia = _moi_truong()
db.open_store = lambda secrets: store
notifier.from_secrets = lambda secrets: telegram_gia

st.warning("CHẾ ĐỘ CHẠY THỬ: dữ liệu mẫu nằm trong bộ nhớ, không lưu lại và mất khi tắt app. "
           "Không có tin Telegram nào được gửi đi.")
if "user" not in st.session_state:
    st.info("Tài khoản mẫu — Quản lý: QL01, PIN 1111. "
            "Nhân viên: NV01 đến NV05, PIN 1234 (hoặc số điện thoại 0912345671 đến 0912345675). "
            "Mở thêm một tab trình duyệt để đăng nhập hai vai cùng lúc.")

try:
    runpy.run_path(APP, run_name="__main__")
finally:
    ten_theo_chat = {f"demo-{i}": ten for i, ten, *_ in NHAN_SU}
    with st.sidebar.expander(f"📨 Tin Telegram giả lập ({len(telegram_gia.tin)})"):
        if not telegram_gia.tin:
            st.caption("Chưa có tin nào. Thử giao việc, báo cáo hoặc duyệt.")
        for chat_id, noi_dung in reversed(telegram_gia.tin[-10:]):
            st.caption(f"Gửi tới {ten_theo_chat.get(chat_id, chat_id)}")
            st.code(noi_dung, language=None, wrap_lines=True)
