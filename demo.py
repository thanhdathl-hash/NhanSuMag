"""Chế độ chạy thử: xem app với dữ liệu mẫu, không cần Google Sheet, service account hay bot Telegram.

    streamlit run demo.py

Dữ liệu nằm trong bộ nhớ, dùng chung cho mọi tab trình duyệt và mất khi tắt app.
Tin Telegram và sự kiện Google Calendar không được gửi đi đâu cả; chúng hiện ở thanh bên
để bạn thấy app sẽ nhắn gì và đẩy gì lên lịch.
File này KHÔNG dùng để triển khai. App thật vẫn là app.py.
"""
import io
import pathlib
import runpy
from datetime import timedelta

import streamlit as st

import config as c
import db
import gcal
import kpi
import notifier
import services
from tests.fakes import FakeCalendar, FakeSpreadsheet, FakeWorksheet

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


def _lich_mau(hom_nay):
    """Vài mục lịch trình cá nhân của quản lý và của Nguyễn An."""
    thu_hai = hom_nay - timedelta(days=hom_nay.weekday())

    def muc(so, id_nv, noi_dung, ngay, bat_dau="", ket_thuc="", lap=c.LAP_KHONG, lap_den=None, xong=""):
        return {c.COL_ID_LICH: f"L-demo{so:04d}", c.COL_ID_NV: id_nv, c.COL_NOI_DUNG: noi_dung,
                c.COL_NGAY: ngay.isoformat(), c.COL_GIO_BAT_DAU: bat_dau, c.COL_GIO_KET_THUC: ket_thuc,
                c.COL_LAP: lap, c.COL_LAP_DEN: "" if lap_den is None else lap_den.isoformat(), c.COL_DA_XONG: xong}

    return [
        muc(1, "QL01", "Họp giao ban", thu_hai, "08:30", "09:00", c.LAP_TUAN, thu_hai + timedelta(days=56),
            xong=thu_hai.isoformat()),
        muc(2, "QL01", "Đi ngân hàng", hom_nay + timedelta(days=2), "14:00"),
        muc(3, "NV01", "Họp giao ban", thu_hai, "08:30", "09:00", c.LAP_TUAN, thu_hai + timedelta(days=56)),
        muc(4, "NV01", "Nộp tiền điện", hom_nay + timedelta(days=1)),
        muc(5, "NV01", "Tập thể dục", hom_nay, "17:30", "18:15", c.LAP_NGAY, hom_nay + timedelta(days=4)),
    ]


def _bang(cols, dong):
    return FakeWorksheet([list(cols)] + [[d.get(k, "") for k in cols] for d in dong])


@st.cache_resource
def _moi_truong():
    nhan_su = [{c.COL_ID_NV: i, c.COL_TEN: ten, c.COL_SDT: sdt, c.COL_MA_PIN: pin,
                c.COL_CHAT_ID: f"demo-{i}", c.COL_ROLE: role,
                c.COL_LICH_GOOGLE: f"lich-{i.lower()}@demo"} for i, ten, sdt, pin, role in NHAN_SU]
    mau = [dict(zip(c.MAU_COLS, m)) for m in MAU]
    store = db.SheetStore(FakeSpreadsheet({
        c.SHEET_NHAN_SU: _bang(c.NHAN_SU_COLS, nhan_su),
        c.SHEET_MAU: _bang(c.MAU_COLS, mau),
        c.SHEET_VIEC: _bang(c.VIEC_COLS, _viec_mau(services.hom_nay())),
        c.SHEET_LICH: _bang(c.LICH_COLS, _lich_mau(services.hom_nay())),
    }))
    gia = DemoNotifier()
    gia.anh[ANH_MAU] = _anh_mau()
    return store, gia, FakeCalendar()


store, telegram_gia, lich_gia = _moi_truong()
db.open_store = lambda secrets: store
notifier.from_secrets = lambda secrets: telegram_gia
gcal.from_secrets = lambda secrets: lich_gia

st.warning("CHẾ ĐỘ CHẠY THỬ: dữ liệu mẫu nằm trong bộ nhớ, không lưu lại và mất khi tắt app. "
           "Không có tin Telegram hay sự kiện Google Calendar nào được gửi đi.")
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
    ten_theo_lich = {f"lich-{i.lower()}@demo": ten for i, ten, *_ in NHAN_SU}
    with st.sidebar.expander(f"📅 Google Calendar giả lập ({len(lich_gia.events)} tạo, {len(lich_gia.deleted)} xóa)"):
        if not lich_gia.events:
            st.caption("Chưa có sự kiện nào. Thử giao việc hoặc thêm lịch trình cá nhân.")
        for e in reversed(lich_gia.events[-10:]):
            gio = "cả ngày" if e["gio_bat_dau"] is None else e["gio_bat_dau"].strftime("%H:%M")
            lap = f", {e['lap'].lower()} đến {e['lap_den']}" if e["lap_den"] else ""
            st.caption(f"Lịch của {ten_theo_lich.get(e['calendar_id'], e['calendar_id'])}")
            st.code(f"{e['summary']}\n{e['ngay']} · {gio}{lap}", language=None, wrap_lines=True)
