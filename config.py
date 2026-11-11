"""Nơi duy nhất khai báo tên bảng, tên cột, trạng thái, hệ số và câu thông báo dùng chung.

Đổi tên một cột trên Google Sheet thì chỉ sửa ở đây (và trong apps_script/nhac_viec.gs).
"""

# Múi giờ dùng để tính "hôm nay"
TZ = "Asia/Ho_Chi_Minh"

# --- Tên bảng ---
SHEET_NHAN_SU, SHEET_MAU, SHEET_VIEC = "Danh_Sach_Nhan_Su", "Thu_Vien_Mau", "Data_Giao_Viec"

# --- Cột bảng nhân sự ---
COL_ID_NV, COL_TEN, COL_SDT, COL_MA_PIN = "ID_NV", "Ten", "SDT", "Ma_PIN"
COL_CHAT_ID, COL_ROLE, COL_KPI_QUY = "Telegram_ChatID", "Role", "KPI_Quy"
NHAN_SU_COLS = [COL_ID_NV, COL_TEN, COL_SDT, COL_MA_PIN, COL_CHAT_ID, COL_ROLE, COL_KPI_QUY]

# --- Cột bảng mẫu việc ---
COL_ID_MAU, COL_TEN_VIEC, COL_MO_TA, COL_TRONG_SO_DIEM = "ID_Mau", "Ten_Viec", "Mo_Ta", "Trong_So_Diem"
MAU_COLS = [COL_ID_MAU, COL_TEN_VIEC, COL_MO_TA, COL_TRONG_SO_DIEM]

# --- Cột bảng giao việc ---
COL_ID_VIEC, COL_NGUOI_NHAN, COL_TRONG_SO = "ID_Viec", "Nguoi_Nhan", "Trong_So"
COL_NGAY_GIAO, COL_HAN_CHOT, COL_TRANG_THAI = "Ngay_Giao", "Han_Chot", "Trang_Thai"
COL_LINK, COL_NGAY_HOAN_THANH = "Link_Chung_Minh", "Ngay_Hoan_Thanh"
COL_SAO, COL_DIEM, COL_GHI_CHU_QL = "Danh_Gia_Sao", "Diem_KPI_Nhan", "Ghi_Chu_QL"
COL_THANG, COL_QUY = "Thang", "Quy"
VIEC_COLS = [
    COL_ID_VIEC, COL_TEN_VIEC, COL_MO_TA, COL_NGUOI_NHAN, COL_TRONG_SO,
    COL_NGAY_GIAO, COL_HAN_CHOT, COL_TRANG_THAI, COL_LINK, COL_NGAY_HOAN_THANH,
    COL_SAO, COL_DIEM, COL_GHI_CHU_QL, COL_THANG, COL_QUY,
]

SHEET_COLS = {SHEET_NHAN_SU: NHAN_SU_COLS, SHEET_MAU: MAU_COLS, SHEET_VIEC: VIEC_COLS}
# Cột khóa của từng bảng
SHEET_KEY = {SHEET_NHAN_SU: COL_ID_NV, SHEET_MAU: COL_ID_MAU, SHEET_VIEC: COL_ID_VIEC}

# --- Trạng thái ---
TT_MOI_GIAO, TT_DANG_LAM, TT_CHO_DUYET = "Mới giao", "Đang làm", "Chờ duyệt"
TT_HOAN_THANH, TT_LAM_LAI = "Hoàn thành", "Làm lại"
TRANG_THAI = [TT_MOI_GIAO, TT_DANG_LAM, TT_CHO_DUYET, TT_HOAN_THANH, TT_LAM_LAI]
# Việc nhân viên chưa nộp: dùng cho danh sách quá hạn và nhắc việc 8h
TT_CHUA_NOP = [TT_MOI_GIAO, TT_DANG_LAM, TT_LAM_LAI]

# --- Vai trò ---
ROLE_QUAN_LY, ROLE_NHAN_VIEN = "QuanLy", "NhanVien"

# --- KPI ---
TRONG_SO_MIN, TRONG_SO_MAX = 1, 5
H1_PHAT_MOI_NGAY, H1_SAN = 0.05, 0.5
H2_THEO_SAO = {5: 1.2, 4: 1.0, 3: 0.8, 2: 0.7, 1: 0.6}

# --- Đăng nhập ---
SO_LAN_SAI_TOI_DA, KHOA_PHUT = 5, 15

# --- Telegram ---
TELEGRAM_TIMEOUT = 10
TG_PREFIX = "tg:"
# Bot API (theo tài liệu đã biết, chưa tra lại được từ môi trường viết code): sendPhoto tối đa 10 MB,
# getFile tải về tối đa 20 MB. Kiểm tra lại trên core.telegram.org/bots/api khi triển khai.
ANH_MAX_BYTES = 5 * 1024 * 1024
TG_CAPTION_MAX, TG_TEXT_MAX = 1024, 4096

# --- Cache đọc Sheet ---
CACHE_TTL_GIAY = 30

# --- Câu thông báo dùng chung ---
MSG_DANG_NHAP_SAI = "Thông tin đăng nhập không đúng."
MSG_TAI_KHOAN_KHOA = "Nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút."
MSG_DA_LUU = "Đã lưu."
MSG_DA_LUU_CHUA_GUI = "Đã lưu nhưng chưa gửi được thông báo Telegram."
MSG_LOI_QUYEN_SHEET = ("Google từ chối truy cập file Sheet. Hãy kiểm tra: file đã được chia sẻ cho email của "
                       "service account với quyền Người chỉnh sửa, và Google Sheets API đã được bật.")
MSG_LOI_XAC_THUC = ("Google không chấp nhận khóa service account. Hãy kiểm tra mục [gcp_service_account] "
                    "trong secrets.")
MSG_LOI_SECRETS = ("Phần secrets của app thiếu hoặc sai định dạng (sheet_id, gcp_service_account). "
                   "Hãy chép lại từ file khóa JSON theo README mục 4.")
MSG_LOI_SHEET = "Không kết nối được Google Sheets. Dữ liệu bạn nhập vẫn còn, vui lòng thử lại."

# --- Tên cột của bảng kết quả KPI do services.kpi_table trả về ---
KQ_KPI, KQ_HOAN_THANH, KQ_TONG_VIEC = "KPI", "Hoan_Thanh", "Tong_Viec"
