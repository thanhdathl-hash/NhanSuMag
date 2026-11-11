# Hệ thống Giao việc và KPI quý: Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây app Streamlit để 1 quản lý giao việc cho 5 nhân viên, theo dõi tiến độ, nghiệm thu và tính KPI quý, dữ liệu trên Google Sheets, thông báo qua Telegram, chi phí vận hành bằng 0.

**Architecture:** Phụ thuộc một chiều: `app.py` → `services.py`, `auth.py` → `db.py`, `kpi.py`, `notifier.py`; mọi module đọc hằng số từ `config.py`. `services.py` nhận `store` và `notifier` qua tham số, nên test thay bằng đồ giả trong bộ nhớ. `kpi.py` chỉ gồm hàm thuần.

**Tech Stack:** Python 3.12, Streamlit, gspread, google-auth, pandas, requests, pytest. Google Apps Script cho nhắc việc 8h.

**Spec:** `docs/superpowers/specs/2026-11-11-he-thong-giao-viec-kpi-design.md`. Người thực hiện đọc cả spec lẫn kế hoạch này.

**Quyết định đã xác nhận ngày 2026-11-11:**

- D1 = A: mục tiêu quý là tổng `Trong_So` các việc được giao có hạn trong quý. App ghi KPI quý hiện tại vào cột `KPI_Quy` sau mỗi lần duyệt.
- D2 = ID hoặc SĐT cộng mã PIN.

## Global Constraints

- Giao diện, thông báo, comment và thông điệp commit bằng tiếng Việt.
- Tên bảng, tên cột, tên trạng thái, hệ số và câu thông báo dùng chung chỉ khai báo trong `config.py`. Task 1 có test quét mã nguồn để giữ quy ước này.
- `kpi.py`: không đọc Sheet, không đọc đồng hồ, không import `streamlit`, `gspread`, `requests`. Ngày nhận qua tham số.
- `app.py` không gọi `store.append_task`, `store.update_*` hay `notifier.*` trực tiếp, trừ `notifier.fetch_photo` để hiển thị ảnh. Mọi thao tác ghi đi qua `services.py`.
- Ngày lưu dạng chuỗi `YYYY-MM-DD`. "Hôm nay" lấy từ `services.hom_nay()` (múi giờ `Asia/Ho_Chi_Minh`, dùng `zoneinfo`). Không dùng `date.today()`.
- Mọi lần ghi Sheet dùng `value_input_option="RAW"`. Mọi lần đọc dùng `value_render_option="UNFORMATTED_VALUE"` rồi đổi từng ô sang `str`.
- Ghi Sheet trước, gửi Telegram sau. Telegram lỗi không hủy thao tác, trừ ảnh chứng minh: `sendPhoto` phải thành công rồi mới ghi.
- Mỗi lần gọi Telegram có `timeout=10`. Tin nhắn gửi dạng văn bản thuần, không dùng `parse_mode`.
- Token bot không xuất hiện trong HTML, URL ảnh, log hay thông báo lỗi.
- Test không chạm Sheet thật, không gọi Telegram thật.
- Không commit `.streamlit/secrets.toml`, khóa service account, token bot, ID file Sheet.
- Không làm các mục ngoài phạm vi: sửa/xóa việc trong app, nhiều quản lý, offline, nhắc việc quá hạn.
- Mỗi task kết thúc bằng `pytest` xanh toàn bộ rồi mới commit.

## Review Focus

Spec nói quản lý sẽ sửa thẳng trên Sheet, nên dữ liệu bẩn là chuyện thường ngày. Năm tình huống dưới đây đã được gắn test vào task tương ứng.

1. **Ô bị sửa tay trên Sheet** (ngày gõ sai định dạng, `Trong_So` để trống hoặc gõ chữ, `Diem_KPI_Nhan` có dấu phẩy). App không được sập: KPI coi ô hỏng là 0, danh sách quá hạn bỏ qua dòng hỏng, `approve_task` báo lỗi nêu rõ ô nào sai. Test ở Task 3, 4, 9, 10.
2. **`Ma_PIN` để trống trên Sheet.** Đăng nhập với PIN rỗng phải thất bại, không được coi hai chuỗi rỗng là khớp. Test ở Task 5.
3. **SĐT nhiều kiểu viết** (`+84 912.345.678`, `84912345678`, `912345678` do Sheet nuốt số 0 đầu) và hai nhân viên trùng SĐT. Các kiểu viết phải khớp cùng một người; trùng SĐT thì từ chối đăng nhập. Test ở Task 5.
4. **Bấm hai lần hoặc tab cũ.** Duyệt lần hai bị từ chối và điểm không cộng đôi; việc đã bị xóa khỏi Sheet thì báo "không tìm thấy việc"; Sheet có 0 hoặc 2 dòng `QuanLy` thì báo lỗi rõ ràng. Test ở Task 8, 9.
5. **Telegram thiếu hoặc quá dài.** Người nhận chưa có `Telegram_ChatID` thì thao tác vẫn lưu và giao diện báo chưa gửi được; chú thích ảnh dài hơn 1024 ký tự hoặc tin dài hơn 4096 ký tự được cắt bớt thay vì gửi lỗi. Test ở Task 6, 7.

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `config.py` | Hằng số: tên bảng, cột, trạng thái, vai trò, hệ số KPI, giới hạn, câu thông báo dùng chung |
| `kpi.py` | Hàm thuần: điểm một việc, quý/tháng của một ngày, mục tiêu và KPI quý |
| `db.py` | `SheetStore` bọc một `gspread.Spreadsheet`; `open_store(secrets)` |
| `auth.py` | Chuẩn hóa SĐT, `LoginGuard`, `authenticate` |
| `notifier.py` | `Notifier` (gửi tin, gửi ảnh, tải ảnh) và các hàm soạn nội dung T1, T3, T4 |
| `services.py` | Năm thao tác ghi, các hàm đọc cho giao diện, `hom_nay()` |
| `app.py` | Giao diện Streamlit |
| `apps_script/nhac_viec.gs` | Nhắc việc 8h (T2) |
| `tests/fakes.py` | `FakeSpreadsheet`, `FakeWorksheet`, `FakeNotifier`, `make_store` |
| `tests/conftest.py` | Dữ liệu mẫu và fixture dùng chung |

Chỉ có một lớp dữ liệu giả: `FakeSpreadsheet` giả lập gspread, còn `SheetStore` thật chạy bên trên. Nhờ vậy test của `services.py` chạy qua cả mã đọc/ghi thật của `db.py`.

---

### Task 1: Khung dự án và `config.py`

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pytest.ini`, `.streamlit/secrets.toml.example`, `config.py`
- Test: `tests/test_config.py`, `tests/test_quy_uoc.py`

**Interfaces:**
- Produces (toàn bộ hằng số trong `config.py`, các task sau dùng đúng tên này):

```python
TZ = "Asia/Ho_Chi_Minh"

SHEET_NHAN_SU, SHEET_MAU, SHEET_VIEC = "Danh_Sach_Nhan_Su", "Thu_Vien_Mau", "Data_Giao_Viec"

COL_ID_NV, COL_TEN, COL_SDT, COL_MA_PIN = "ID_NV", "Ten", "SDT", "Ma_PIN"
COL_CHAT_ID, COL_ROLE, COL_KPI_QUY = "Telegram_ChatID", "Role", "KPI_Quy"
NHAN_SU_COLS = [COL_ID_NV, COL_TEN, COL_SDT, COL_MA_PIN, COL_CHAT_ID, COL_ROLE, COL_KPI_QUY]

COL_ID_MAU, COL_TEN_VIEC, COL_MO_TA, COL_TRONG_SO_DIEM = "ID_Mau", "Ten_Viec", "Mo_Ta", "Trong_So_Diem"
MAU_COLS = [COL_ID_MAU, COL_TEN_VIEC, COL_MO_TA, COL_TRONG_SO_DIEM]

COL_ID_VIEC, COL_NGUOI_NHAN, COL_TRONG_SO = "ID_Viec", "Nguoi_Nhan", "Trong_So"
COL_NGAY_GIAO, COL_HAN_CHOT, COL_TRANG_THAI = "Ngay_Giao", "Han_Chot", "Trang_Thai"
COL_LINK, COL_NGAY_HOAN_THANH = "Link_Chung_Minh", "Ngay_Hoan_Thanh"
COL_SAO, COL_DIEM, COL_GHI_CHU_QL = "Danh_Gia_Sao", "Diem_KPI_Nhan", "Ghi_Chu_QL"
COL_THANG, COL_QUY = "Thang", "Quy"
VIEC_COLS = [COL_ID_VIEC, COL_TEN_VIEC, COL_MO_TA, COL_NGUOI_NHAN, COL_TRONG_SO,
             COL_NGAY_GIAO, COL_HAN_CHOT, COL_TRANG_THAI, COL_LINK, COL_NGAY_HOAN_THANH,
             COL_SAO, COL_DIEM, COL_GHI_CHU_QL, COL_THANG, COL_QUY]
SHEET_COLS = {SHEET_NHAN_SU: NHAN_SU_COLS, SHEET_MAU: MAU_COLS, SHEET_VIEC: VIEC_COLS}

TT_MOI_GIAO, TT_DANG_LAM, TT_CHO_DUYET = "Mới giao", "Đang làm", "Chờ duyệt"
TT_HOAN_THANH, TT_LAM_LAI = "Hoàn thành", "Làm lại"
TRANG_THAI = [TT_MOI_GIAO, TT_DANG_LAM, TT_CHO_DUYET, TT_HOAN_THANH, TT_LAM_LAI]
TT_CHUA_NOP = [TT_MOI_GIAO, TT_DANG_LAM, TT_LAM_LAI]   # dùng cho việc quá hạn và T2

ROLE_QUAN_LY, ROLE_NHAN_VIEN = "QuanLy", "NhanVien"

TRONG_SO_MIN, TRONG_SO_MAX = 1, 5
H1_PHAT_MOI_NGAY, H1_SAN = 0.05, 0.5
H2_THEO_SAO = {5: 1.2, 4: 1.0, 3: 0.8, 2: 0.7, 1: 0.6}

SO_LAN_SAI_TOI_DA, KHOA_PHUT = 5, 15
TELEGRAM_TIMEOUT = 10
TG_PREFIX = "tg:"
ANH_MAX_BYTES = 5 * 1024 * 1024
TG_CAPTION_MAX, TG_TEXT_MAX = 1024, 4096
CACHE_TTL_GIAY = 30

MSG_DANG_NHAP_SAI = "Thông tin đăng nhập không đúng."
MSG_TAI_KHOAN_KHOA = "Nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút."
MSG_DA_LUU = "Đã lưu."
MSG_DA_LUU_CHUA_GUI = "Đã lưu nhưng chưa gửi được thông báo Telegram."
MSG_LOI_SHEET = "Không kết nối được Google Sheets. Dữ liệu bạn nhập vẫn còn, vui lòng thử lại."
```

- [ ] **Step 1: Tạo `.gitignore` trước mọi file khác**

Nội dung: `.streamlit/secrets.toml`, `*.json` khóa service account (`service_account*.json`, `*-credentials.json`), `__pycache__/`, `.pytest_cache/`, `.venv/`. Kiểm tra: `git check-ignore .streamlit/secrets.toml` in ra đường dẫn.

- [ ] **Step 2: Tạo `requirements.txt`, `pytest.ini`, `.streamlit/secrets.toml.example`**

Trước khi ghim phiên bản, mở trang tài liệu Streamlit Community Cloud để xem các bản Python đang được hỗ trợ, ghi bản đã chọn vào README ở Task 13. Ghim `streamlit`, `gspread`, `google-auth`, `pandas`, `requests`, `pytest` bằng `==` ở bản mới nhất cài được cùng nhau trên bản Python đó (mốc tham khảo trong CLAUDE.md: streamlit 1.67.0, gspread 6.2.1, pandas 3.0.5). `pytest.ini`: `testpaths = tests`, `pythonpath = .`.

`secrets.toml.example` có đúng ba khóa, toàn giá trị giả: `sheet_id`, `telegram_bot_token`, và bảng `[gcp_service_account]` với các trường của file khóa JSON.

- [ ] **Step 3: Viết test thất bại**

```python
# tests/test_config.py
import config

def test_nam_trang_thai_dung_thu_tu_spec():
    assert config.TRANG_THAI == ["Mới giao", "Đang làm", "Chờ duyệt", "Hoàn thành", "Làm lại"]

def test_h2_theo_bang_spec():
    assert config.H2_THEO_SAO == {5: 1.2, 4: 1.0, 3: 0.8, 2: 0.7, 1: 0.6}

def test_cot_bang_viec_dung_thu_tu_spec():
    assert config.VIEC_COLS == ["ID_Viec", "Ten_Viec", "Mo_Ta", "Nguoi_Nhan", "Trong_So",
        "Ngay_Giao", "Han_Chot", "Trang_Thai", "Link_Chung_Minh", "Ngay_Hoan_Thanh",
        "Danh_Gia_Sao", "Diem_KPI_Nhan", "Ghi_Chu_QL", "Thang", "Quy"]

def test_cot_nhan_su_va_mau():
    assert config.NHAN_SU_COLS == ["ID_NV", "Ten", "SDT", "Ma_PIN", "Telegram_ChatID", "Role", "KPI_Quy"]
    assert config.MAU_COLS == ["ID_Mau", "Ten_Viec", "Mo_Ta", "Trong_So_Diem"]
```

```python
# tests/test_quy_uoc.py
# Quét kpi.py, db.py, auth.py, notifier.py, services.py, app.py (file nào chưa có thì bỏ qua).
import pathlib, re, config

MODULES = ["kpi.py", "db.py", "auth.py", "notifier.py", "services.py", "app.py"]
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
```

- [ ] **Step 4: Chạy để thấy thất bại**

Run: `pytest tests/test_config.py -v` → FAIL `ModuleNotFoundError: config`.

- [ ] **Step 5: Viết `config.py` đúng khối Interfaces ở trên**

- [ ] **Step 6: Chạy `pytest -v`** → PASS toàn bộ.

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt pytest.ini .streamlit/secrets.toml.example config.py tests/
git commit -m "Khung dự án và config.py"
```

---

### Task 2: `kpi.py`, điểm của một việc

**Files:**
- Create: `kpi.py`
- Test: `tests/test_kpi_diem.py`

**Interfaces:**
- Consumes: `config.H1_PHAT_MOI_NGAY`, `H1_SAN`, `H2_THEO_SAO`.
- Produces:
  - `days_late(han_chot: date, ngay_hoan_thanh: date) -> int` (không nhỏ hơn 0)
  - `h1(days_late: int) -> float`
  - `h2(stars: int) -> float` (ngoài 1..5 thì `ValueError`)
  - `task_score(trong_so: int, days_late: int, stars: int) -> float` (làm tròn 2 chữ số)
  - `quarter_of(d: date) -> str` (`"2026-Q4"`), `month_of(d: date) -> str` (`"2026-11"`)

- [ ] **Step 1: Viết test thất bại**

```python
from datetime import date
import pytest, kpi

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
```

- [ ] **Step 2: Chạy** `pytest tests/test_kpi_diem.py -v` → FAIL `ModuleNotFoundError: kpi`.
- [ ] **Step 3: Viết sáu hàm trong `kpi.py`.** `h1 = max(H1_SAN, 1 - H1_PHAT_MOI_NGAY * d)`; `task_score = round(trong_so * h1 * h2, 2)`.
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "kpi: điểm một việc, quý và tháng"`

---

### Task 3: `kpi.py`, KPI quý

**Files:**
- Modify: `kpi.py`
- Test: `tests/test_kpi_quy.py`

**Interfaces:**
- Consumes: `config.COL_TRONG_SO`, `COL_DIEM`, `COL_TRANG_THAI`, `TT_HOAN_THANH`.
- Produces (tham số `tasks` là DataFrame **đã lọc sẵn** theo một nhân viên và một quý; mọi ô là `str`):
  - `quarter_target(tasks: pd.DataFrame) -> float`: tổng `Trong_So` mọi trạng thái. Đây là nơi duy nhất chứa D1.
  - `quarter_kpi(tasks: pd.DataFrame) -> float | None`: phần trăm làm tròn 2 chữ số; `None` khi mục tiêu bằng 0.
  - `quarter_progress(tasks: pd.DataFrame) -> tuple[int, int]`: (số việc `Hoàn thành`, tổng số việc).

- [ ] **Step 1: Viết test thất bại**

```python
import pandas as pd, kpi, config as c

def bang(*dong):  # mỗi dòng: (trong_so, trang_thai, diem), đều là chuỗi
    return pd.DataFrame([{c.COL_TRONG_SO: t, c.COL_TRANG_THAI: s, c.COL_DIEM: d} for t, s, d in dong],
                        columns=[c.COL_TRONG_SO, c.COL_TRANG_THAI, c.COL_DIEM])

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
```

- [ ] **Step 2: Chạy** → FAIL `AttributeError: quarter_target`.
- [ ] **Step 3: Viết ba hàm.** Đổi chuỗi sang số bằng một hàm nội bộ: thay `,` bằng `.`, rồi `pd.to_numeric(errors="coerce").fillna(0)`.
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "kpi: mục tiêu và KPI quý (D1-A)"`

---

### Task 4: `db.py` và lớp gspread giả

**Files:**
- Create: `db.py`, `tests/fakes.py`, `tests/conftest.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `config.SHEET_COLS`, các hằng tên bảng và cột.
- Produces trong `db.py`:

```python
class StoreError(Exception): ...          # lỗi kết nối; thông điệp là config.MSG_LOI_SHEET
class SchemaError(StoreError): ...        # thiếu bảng hoặc thiếu cột
class TaskNotFound(StoreError): ...

class SheetStore:
    def __init__(self, spreadsheet): ...                 # gspread.Spreadsheet hoặc FakeSpreadsheet
    def check_headers(self) -> None                      # SchemaError: "Bảng Data_Giao_Viec thiếu cột: Quy, Thang"
    def employees(self) -> pd.DataFrame                  # cột = NHAN_SU_COLS, mọi ô là str, ô trống là ""
    def templates(self) -> pd.DataFrame
    def tasks(self) -> pd.DataFrame
    def get_task(self, id_viec: str) -> dict | None      # luôn đọc mới từ Sheet
    def append_task(self, task: dict) -> None            # task có đủ khóa VIEC_COLS
    def update_task(self, id_viec: str, fields: dict) -> None       # TaskNotFound nếu không có
    def update_employee(self, id_nv: str, fields: dict) -> None

def open_store(secrets) -> SheetStore    # gspread.service_account_from_dict(...).open_by_key(secrets["sheet_id"])
```

- Produces trong `tests/fakes.py`:
  - `FakeWorksheet(rows: list[list])` với `get_values(value_render_option=None)`, `col_values(col: int)`, `append_row(values, value_input_option=None, table_range=None)`, `batch_update(data, value_input_option=None)`. Hai hàm ghi `assert value_input_option == "RAW"`. `get_values` cắt các ô trống cuối dòng như gspread thật. Thuộc tính `fail_with: Exception | None` để giả lập mất mạng.
  - `FakeSpreadsheet(sheets: dict[str, FakeWorksheet])` với `worksheet(name)`, ném `gspread.WorksheetNotFound` khi thiếu.
  - `make_store(employees: list[dict], templates: list[dict] = (), tasks: list[dict] = ()) -> SheetStore`
  - `FakeNotifier` (dùng từ Task 7): thuộc tính `ok: bool = True`, `sent: list[tuple]`; `send_message(chat_id, text) -> bool`, `send_photo(chat_id, photo, filename, caption) -> str | None` (trả `"FILE123"` khi `ok`), `fetch_photo(file_id) -> bytes | None`. Chat ID rỗng trả thất bại như `Notifier` thật.
- Produces trong `tests/conftest.py`:
  - `NHAN_SU`: `QL01` (Trần Quản Lý, `0900000001`, PIN `1111`, chat `100`, `QuanLy`), `NV01` (Nguyễn An, `0912345678`, PIN `1234`, chat `201`, `NhanVien`), `NV02` (Lê Bình, `0987654321`, PIN `5678`, chat `""`, `NhanVien`).
  - Fixture `store`, `notifier`, `ql`, `nv1`, `nv2` (dict người dùng không có `Ma_PIN`), và hàm `viec(**ghi_de) -> dict` trả một dòng việc đủ cột với mặc định: `ID_Viec="V-00000001"`, người nhận `NV01`, trọng số `"3"`, hạn `2026-11-20`, trạng thái `Mới giao`, quý `2026-Q4`.

- [ ] **Step 1: Viết `tests/fakes.py` và `tests/conftest.py`** theo Interfaces.

- [ ] **Step 2: Viết test thất bại**

```python
import pytest, requests, config as c, db
from tests.fakes import make_store, FakeSpreadsheet, FakeWorksheet
from tests.conftest import NHAN_SU, viec

def test_doc_tra_ve_chuoi_va_du_cot():                      # Review Focus 1
    s = make_store(NHAN_SU, tasks=[viec(Trong_So=3, Diem_KPI_Nhan=3.24)])   # ô số trên Sheet
    t = s.tasks().iloc[0]
    assert t[c.COL_TRONG_SO] == "3" and t[c.COL_DIEM] == "3.24"
    assert t[c.COL_GHI_CHU_QL] == ""                         # ô trống cuối dòng bị gspread cắt
    assert list(s.tasks().columns) == c.VIEC_COLS

def test_sdt_giu_so_0_dau():
    assert make_store(NHAN_SU).employees().iloc[1][c.COL_SDT] == "0912345678"

def test_bang_viec_trong_van_co_du_cot():
    assert list(make_store(NHAN_SU).tasks().columns) == c.VIEC_COLS

def test_thieu_cot_bao_dung_ten():
    ws = FakeWorksheet([[x for x in c.VIEC_COLS if x not in (c.COL_QUY, c.COL_THANG)]])
    s = db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
                                       c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]), c.SHEET_VIEC: ws}))
    with pytest.raises(db.SchemaError, match="Data_Giao_Viec.*Quy.*Thang"):
        s.check_headers()

def test_thieu_bang_bao_ten_bang():
    with pytest.raises(db.SchemaError, match="Thu_Vien_Mau"):
        db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
                                       c.SHEET_VIEC: FakeWorksheet([c.VIEC_COLS])})).check_headers()

def test_cot_xep_thu_tu_khac_van_doc_ghi_dung():
    dao = list(reversed(c.VIEC_COLS)); d = viec()
    s = db.SheetStore(FakeSpreadsheet({c.SHEET_NHAN_SU: FakeWorksheet([c.NHAN_SU_COLS]),
        c.SHEET_MAU: FakeWorksheet([c.MAU_COLS]), c.SHEET_VIEC: FakeWorksheet([dao, [d[k] for k in dao]])}))
    s.update_task("V-00000001", {c.COL_TRANG_THAI: c.TT_DANG_LAM})
    assert s.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_DANG_LAM
    assert s.get_task("V-00000001")[c.COL_TEN_VIEC] == d[c.COL_TEN_VIEC]

def test_them_roi_sua_viec():
    s = make_store(NHAN_SU)
    s.append_task(viec()); s.append_task(viec(ID_Viec="V-00000002"))
    s.update_task("V-00000002", {c.COL_TRANG_THAI: c.TT_CHO_DUYET, c.COL_LINK: "https://a.vn"})
    assert s.get_task("V-00000002")[c.COL_LINK] == "https://a.vn"
    assert s.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_MOI_GIAO

def test_gia_tri_bat_dau_bang_dau_bang_duoc_luu_nguyen_van():     # RAW, không thành công thức
    s = make_store(NHAN_SU); s.append_task(viec(Ten_Viec="=1+1"))
    assert s.get_task("V-00000001")[c.COL_TEN_VIEC] == "=1+1"

def test_khong_tim_thay_viec():
    s = make_store(NHAN_SU)
    assert s.get_task("V-khongco") is None
    with pytest.raises(db.TaskNotFound):
        s.update_task("V-khongco", {c.COL_TRANG_THAI: c.TT_DANG_LAM})

def test_cap_nhat_kpi_quy_nhan_vien():
    s = make_store(NHAN_SU); s.update_employee("NV01", {c.COL_KPI_QUY: "49.57"})
    assert s.employees().iloc[1][c.COL_KPI_QUY] == "49.57"

def test_mat_mang_thanh_store_error():
    s = make_store(NHAN_SU)
    s._spreadsheet.worksheet(c.SHEET_VIEC).fail_with = requests.ConnectionError("x")
    with pytest.raises(db.StoreError):
        s.tasks()
```

- [ ] **Step 3: Chạy** `pytest tests/test_db.py -v` → FAIL `ModuleNotFoundError: db`.

- [ ] **Step 4: Viết `db.py`.** Các lựa chọn đã chốt:
  - Đọc: `ws.get_values(value_render_option="UNFORMATTED_VALUE")`; dòng đầu là tiêu đề; đệm mỗi dòng cho đủ độ dài tiêu đề; đổi mọi ô sang `str` (số nguyên dạng `3.0` thành `"3"`); chỉ giữ các cột khai báo trong `config`, tra theo tên chứ không theo vị trí.
  - `update_*`: đọc lại tiêu đề và `ws.col_values(<cột khóa>)` ngay lúc ghi để tìm số dòng, rồi `ws.batch_update([{"range": <A1>, "values": [[v]]}, ...], value_input_option="RAW")`. Dùng `gspread.utils.rowcol_to_a1`.
  - `append_task`: xếp giá trị theo thứ tự tiêu đề thật của Sheet, `ws.append_row(values, value_input_option="RAW", table_range="A1")`.
  - Bọc `gspread.exceptions.GSpreadException` và `requests.RequestException` thành `StoreError(config.MSG_LOI_SHEET)`; `WorksheetNotFound` trong `check_headers` thành `SchemaError`.
  - Lưu spreadsheet ở `self._spreadsheet`.

- [ ] **Step 5: Chạy `pytest -v`** → PASS.
- [ ] **Step 6: Commit** `git commit -m "db: SheetStore và lớp gspread giả cho test"`

---

### Task 5: `auth.py`

**Files:**
- Create: `auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `config.COL_*` của bảng nhân sự, `SO_LAN_SAI_TOI_DA`, `KHOA_PHUT`, `MSG_DANG_NHAP_SAI`, `MSG_TAI_KHOAN_KHOA`.
- Produces:

```python
def normalize_phone(s: str) -> str
class LoginGuard:                       # bộ đếm trong bộ nhớ; app giữ bằng st.cache_resource
    def is_locked(self, key: str, now: datetime) -> bool
    def record_failure(self, key: str, now: datetime) -> None
    def reset(self, key: str) -> None
@dataclass
class AuthResult:
    user: dict | None                   # các cột nhân sự trừ Ma_PIN
    error: str | None
def authenticate(employees: pd.DataFrame, identifier: str, pin: str,
                 guard: LoginGuard, now: datetime) -> AuthResult
```

- [ ] **Step 1: Viết test thất bại**

```python
from datetime import datetime, timedelta, timezone
import pytest, auth, config as c
from tests.fakes import make_store
from tests.conftest import NHAN_SU

T0 = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
def ns(them=()): return make_store(list(NHAN_SU) + list(them)).employees()
def vao(ident, pin, guard=None, now=T0, bang=None):
    return auth.authenticate(ns() if bang is None else bang, ident, pin, guard or auth.LoginGuard(), now)

@pytest.mark.parametrize("raw", ["0912345678", "0912 345 678", "0912.345.678", "+84912345678",
                                 "+84 912.345.678", "84912345678", "912345678", " 0912345678 "])
def test_chuan_hoa_sdt(raw):                                   # Review Focus 3
    assert auth.normalize_phone(raw) == "0912345678"

@pytest.mark.parametrize("ident", ["NV01", "nv01", " NV01 ", "0912345678", "+84 912 345 678"])
def test_dung_pin(ident):
    r = vao(ident, "1234")
    assert r.error is None and r.user[c.COL_ID_NV] == "NV01" and c.COL_MA_PIN not in r.user

def test_sai_pin_va_id_khong_ton_tai_cung_mot_thong_bao():
    assert vao("NV01", "0000").error == vao("NV99", "0000").error == c.MSG_DANG_NHAP_SAI
    assert vao("NV01", "0000").user is None

def test_pin_trong_tren_sheet_khong_dang_nhap_duoc():          # Review Focus 2
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03", c.COL_SDT: "0911111111", c.COL_MA_PIN: ""}])
    assert vao("NV03", "", bang=bang).user is None
    assert vao("NV01", "").user is None

def test_trung_sdt_thi_tu_choi():                              # Review Focus 3
    bang = ns([{**NHAN_SU[1], c.COL_ID_NV: "NV03"}])           # trùng SĐT với NV01
    assert vao("0912345678", "1234", bang=bang).user is None
    assert vao("NV01", "1234", bang=bang).user is not None     # vào bằng ID vẫn được

def test_khoa_sau_5_lan_sai_ke_ca_khi_dung_pin():
    g = auth.LoginGuard()
    for _ in range(4): vao("NV01", "0000", g)
    assert vao("NV01", "0000", g).error == c.MSG_DANG_NHAP_SAI          # lần thứ 5
    assert vao("NV01", "1234", g).error == c.MSG_TAI_KHOAN_KHOA
    assert vao("0912345678", "1234", g).error == c.MSG_TAI_KHOAN_KHOA   # cùng tài khoản, vào bằng SĐT
    assert vao("NV02", "5678", g).user is not None                      # tài khoản khác không bị ảnh hưởng

def test_het_15_phut_thi_mo_khoa():
    g = auth.LoginGuard()
    for _ in range(5): vao("NV01", "0000", g)
    assert vao("NV01", "1234", g, now=T0 + timedelta(minutes=14, seconds=59)).user is None
    assert vao("NV01", "1234", g, now=T0 + timedelta(minutes=15)).user is not None

def test_dang_nhap_dung_xoa_bo_dem():
    g = auth.LoginGuard()
    for _ in range(4): vao("NV01", "0000", g)
    vao("NV01", "1234", g)
    for _ in range(4): vao("NV01", "0000", g)
    assert vao("NV01", "1234", g).user is not None

def test_id_khong_ton_tai_cung_bi_khoa_de_khong_lo_id_nao_co_that():
    g = auth.LoginGuard()
    for _ in range(5): vao("NV99", "0000", g)
    assert vao("NV99", "0000", g).error == c.MSG_TAI_KHOAN_KHOA
```

- [ ] **Step 2: Chạy** → FAIL `ModuleNotFoundError: auth`.

- [ ] **Step 3: Viết `auth.py`.** Các lựa chọn đã chốt:
  - `normalize_phone`: bỏ khoảng trắng, dấu chấm, dấu gạch; `+84` hoặc `84` đầu (khi phần còn lại có 9 chữ số) đổi thành `0`; chuỗi 9 chữ số không bắt đầu bằng `0` thì thêm `0`.
  - Tìm tài khoản: so `ID_NV` không phân biệt hoa thường sau khi `strip`; nếu không khớp thì so SĐT đã chuẩn hóa ở cả hai phía; SĐT khớp hơn một dòng coi như không tìm thấy.
  - Khóa của bộ đếm: `ID_NV` nếu tìm được tài khoản, ngược lại là chuỗi người dùng nhập sau khi chuẩn hóa.
  - Kiểm tra khóa trước, rồi mới so PIN bằng `hmac.compare_digest` trên bytes UTF-8. PIN lưu trên Sheet rỗng thì luôn thất bại.
  - Khóa bắt đầu từ lần sai thứ 5 và kéo dài `KHOA_PHUT` phút; hết hạn thì bộ đếm về 0.

- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "auth: đăng nhập bằng ID/SĐT và PIN, khóa sau 5 lần sai (D2)"`

---

### Task 6: `notifier.py`

**Files:**
- Create: `notifier.py`
- Test: `tests/test_notifier.py`

**Interfaces:**
- Consumes: `config.TELEGRAM_TIMEOUT`, `TG_CAPTION_MAX`, `TG_TEXT_MAX`, các `COL_*` của bảng việc.
- Produces:

```python
class Notifier:
    def __init__(self, token: str): ...
    def send_message(self, chat_id: str, text: str) -> bool
    def send_photo(self, chat_id: str, photo: bytes, filename: str, caption: str) -> str | None   # file_id
    def fetch_photo(self, file_id: str) -> bytes | None

def msg_t1(task: dict) -> str                       # có Ten_Viec, Han_Chot, Trong_So, Mo_Ta
def msg_t3(task: dict, ten_nv: str, link: str | None) -> str   # có tên NV, Ten_Viec, ID_Viec, Han_Chot, link nếu có
def msg_t4_duyet(task: dict, stars: int, diem: float) -> str
def msg_t4_tra_lai(task: dict, ly_do: str) -> str
```

- [ ] **Step 1: Viết test thất bại.** Dùng `monkeypatch.setattr(requests, "post"/"get", gia)` với hàm giả ghi lại `url`, `kwargs` và trả đối tượng có `.json()`, `.content`, `.status_code`.

```python
TOKEN = "123456:ABC-token-gia"

def test_send_message_thanh_cong(gia_post):        # gia_post trả {"ok": True, "result": {}}
    assert Notifier(TOKEN).send_message("201", "xin chào") is True
    goi = gia_post.calls[0]
    assert goi.url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert goi.kwargs["timeout"] == 10
    assert goi.kwargs["json"] == {"chat_id": "201", "text": "xin chào"}      # không parse_mode

@pytest.mark.parametrize("loi", [requests.ConnectionError("x"), requests.Timeout("x")])
def test_loi_mang_tra_false_khong_nem(monkeypatch, loi): ...   # post ném lỗi → send_message False, send_photo None
def test_telegram_tra_ok_false(gia_post): ...                  # {"ok": False, "description": "chat not found"} → False
def test_phan_hoi_khong_phai_json(gia_post): ...               # .json() ném ValueError → False
def test_chat_id_trong_khong_goi_mang(gia_post):               # Review Focus 5
    assert Notifier(TOKEN).send_message("", "a") is False and gia_post.calls == []

def test_cat_tin_va_chu_thich_qua_dai(gia_post):               # Review Focus 5
    Notifier(TOKEN).send_message("1", "a" * 5000)
    assert len(gia_post.calls[0].kwargs["json"]["text"]) == 4096
    Notifier(TOKEN).send_photo("1", b"x", "a.jpg", "b" * 2000)
    assert len(gia_post.calls[1].kwargs["data"]["caption"]) == 1024

def test_send_photo_tra_file_id_anh_lon_nhat(gia_post):
    gia_post.tra = {"ok": True, "result": {"photo": [{"file_id": "nho"}, {"file_id": "lon"}]}}
    assert Notifier(TOKEN).send_photo("100", b"\xff\xd8", "a.jpg", "chú thích") == "lon"
    assert gia_post.calls[0].url.endswith("/sendPhoto") and "photo" in gia_post.calls[0].kwargs["files"]

def test_fetch_photo(gia_get):     # lần 1 getFile trả {"ok": True, "result": {"file_path": "photos/a.jpg"}}, lần 2 trả content
    assert Notifier(TOKEN).fetch_photo("lon") == b"ANH"
    assert gia_get.calls[1].url == f"https://api.telegram.org/file/bot{TOKEN}/photos/a.jpg"

def test_fetch_photo_loi_tra_none(gia_get): ...                # getFile ok False, hoặc tải về status 404 → None

def test_noi_dung_tin():
    v = viec(Ten_Viec="Báo cáo tuần", Mo_Ta="Gửi trước 17h")
    assert all(x in msg_t1(v) for x in ["Báo cáo tuần", "2026-11-20", "3", "Gửi trước 17h"])
    t3 = msg_t3(v, "Nguyễn An", "https://a.vn")
    assert all(x in t3 for x in ["Nguyễn An", "Báo cáo tuần", "V-00000001", "https://a.vn"])
    assert "None" not in msg_t3(v, "Nguyễn An", None)
    assert all(x in msg_t4_duyet(v, 5, 3.6) for x in ["Báo cáo tuần", "5", "3.6"])
    assert "Thiếu số liệu" in msg_t4_tra_lai(v, "Thiếu số liệu")
```

- [ ] **Step 2: Chạy** → FAIL `ModuleNotFoundError: notifier`.
- [ ] **Step 3: Viết `notifier.py`.** Gọi `requests.post`/`requests.get` qua thuộc tính module (để monkeypatch được), luôn `timeout=config.TELEGRAM_TIMEOUT`. `sendPhoto` gửi multipart: `data={"chat_id", "caption"}`, `files={"photo": (filename, photo)}`. Bắt `requests.RequestException`, `ValueError`, `KeyError`, `IndexError`. Không log URL.
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Kiểm tra giới hạn hiện hành của Bot API** cho `sendPhoto` và `getFile` trên core.telegram.org/bots/api. Nếu giới hạn `sendPhoto` nhỏ hơn 5 MB, hạ `config.ANH_MAX_BYTES` cho khớp và ghi con số vào comment cạnh hằng.
- [ ] **Step 6: Commit** `git commit -m "notifier: gửi tin, gửi ảnh, tải ảnh qua Telegram"`

---

### Task 7: `services.py`, nền và `create_task`

**Files:**
- Create: `services.py`
- Test: `tests/test_services_tao_viec.py`

**Interfaces:**
- Consumes: `db.SheetStore`, `db.TaskNotFound`, `notifier.msg_t1`, `kpi.quarter_of`, `kpi.month_of`, fixture ở `conftest.py`.
- Produces:

```python
class ServiceError(Exception): ...            # thông điệp tiếng Việt, hiện thẳng lên giao diện
class PermissionDenied(ServiceError): ...
class InvalidState(ServiceError): ...
class InvalidInput(ServiceError): ...

@dataclass
class Result:
    task: dict            # dòng việc sau khi ghi
    notified: bool        # False → giao diện hiện config.MSG_DA_LUU_CHUA_GUI
    kpi_saved: bool = True

def hom_nay() -> date                                         # theo config.TZ
def find_manager(employees: pd.DataFrame) -> dict             # ServiceError nếu không có đúng 1 dòng QuanLy
def visible_tasks(tasks: pd.DataFrame, user: dict) -> pd.DataFrame
def create_task(store, notifier, user: dict, *, ten_viec: str, mo_ta: str, nguoi_nhan: str,
                han_chot: date, trong_so: int, today: date) -> Result
```

- [ ] **Step 1: Viết test thất bại**

```python
D = date(2026, 11, 11)
def tao(store, notifier, user, **kw):
    mac_dinh = dict(ten_viec="Báo cáo tuần", mo_ta="", nguoi_nhan="NV01", han_chot=date(2026, 12, 1), trong_so=3, today=D)
    return services.create_task(store, notifier, user, **{**mac_dinh, **kw})

def test_tao_viec_ghi_du_cot(store, notifier, ql):
    r = tao(store, notifier, ql, mo_ta="Gửi trước 17h")
    t = store.tasks().iloc[0]
    assert re.fullmatch(r"V-[0-9a-f]{8}", t[c.COL_ID_VIEC]) and r.task[c.COL_ID_VIEC] == t[c.COL_ID_VIEC]
    assert (t[c.COL_TRANG_THAI], t[c.COL_NGAY_GIAO], t[c.COL_HAN_CHOT]) == (c.TT_MOI_GIAO, "2026-11-11", "2026-12-01")
    assert (t[c.COL_THANG], t[c.COL_QUY], t[c.COL_TRONG_SO]) == ("2026-12", "2026-Q4", "3")
    assert t[c.COL_LINK] == t[c.COL_SAO] == t[c.COL_DIEM] == t[c.COL_NGAY_HOAN_THANH] == ""

def test_quy_theo_han_chot_khong_theo_ngay_giao(store, notifier, ql):
    assert tao(store, notifier, ql, han_chot=date(2027, 1, 5)).task[c.COL_QUY] == "2027-Q1"

def test_t1_gui_cho_nguoi_nhan(store, notifier, ql):
    assert tao(store, notifier, ql).notified is True
    assert notifier.sent[0][0] == "201" and "Báo cáo tuần" in notifier.sent[0][1]

def test_telegram_loi_van_luu(store, notifier, ql):
    notifier.ok = False
    assert tao(store, notifier, ql).notified is False and len(store.tasks()) == 1

def test_nguoi_nhan_chua_co_chat_id_van_luu(store, notifier, ql):          # Review Focus 5
    assert tao(store, notifier, ql, nguoi_nhan="NV02").notified is False and len(store.tasks()) == 1

def test_nhan_vien_khong_duoc_tao(store, notifier, nv1):
    with pytest.raises(services.PermissionDenied): tao(store, notifier, nv1)
    assert len(store.tasks()) == 0

@pytest.mark.parametrize("kw", [{"ten_viec": "  "}, {"trong_so": 0}, {"trong_so": 6}, {"trong_so": 2.5},
                                {"nguoi_nhan": "NV99"}, {"nguoi_nhan": "QL01"}, {"nguoi_nhan": ""}, {"han_chot": None}])
def test_dau_vao_sai_bi_tu_choi_va_khong_ghi(store, notifier, ql, kw):
    with pytest.raises(services.InvalidInput): tao(store, notifier, ql, **kw)
    assert len(store.tasks()) == 0 and notifier.sent == []

def test_id_trung_thi_sinh_lai(store, notifier, ql, monkeypatch):
    it = iter(["aaaaaaaa", "aaaaaaaa", "bbbbbbbb"])
    monkeypatch.setattr(services.secrets, "token_hex", lambda n: next(it))
    tao(store, notifier, ql); tao(store, notifier, ql)
    assert list(store.tasks()[c.COL_ID_VIEC]) == ["V-aaaaaaaa", "V-bbbbbbbb"]

def test_visible_tasks(store, ql, nv1, nv2):
    store.append_task(viec()); store.append_task(viec(ID_Viec="V-00000002", Nguoi_Nhan="NV02"))
    assert len(services.visible_tasks(store.tasks(), ql)) == 2
    assert list(services.visible_tasks(store.tasks(), nv1)[c.COL_ID_VIEC]) == ["V-00000001"]
    assert list(services.visible_tasks(store.tasks(), nv2)[c.COL_ID_VIEC]) == ["V-00000002"]

def test_hom_nay_theo_gio_viet_nam(monkeypatch):
    # giả lập đồng hồ 2026-11-10 18:30 UTC = 2026-11-11 01:30 giờ VN
    ...
    assert services.hom_nay() == date(2026, 11, 11)

def test_find_manager_can_dung_mot_quan_ly():                               # Review Focus 4
    with pytest.raises(services.ServiceError): services.find_manager(make_store(NHAN_SU[1:]).employees())
    with pytest.raises(services.ServiceError):
        services.find_manager(make_store(NHAN_SU + [{**NHAN_SU[0], c.COL_ID_NV: "QL02"}]).employees())
```

- [ ] **Step 2: Chạy** → FAIL `ModuleNotFoundError: services`.
- [ ] **Step 3: Viết phần nền và `create_task`.** Người nhận phải là dòng có `Role = NhanVien`. `trong_so` phải là `int` (không nhận `bool`, `float`). ID: `"V-" + secrets.token_hex(4)`, sinh lại khi trùng với ID đang có. `ten_viec`, `mo_ta` được `strip`. Để `hom_nay()` test được, đọc giờ qua một hàm nội bộ `_now_utc()` mà test monkeypatch.
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "services: tạo việc và thông báo T1"`

---

### Task 8: `services.py`, `start_task` và `submit_task`

**Files:**
- Modify: `services.py`
- Test: `tests/test_services_nhan_vien.py`

**Interfaces:**
- Consumes: `store.get_task`, `store.update_task`, `notifier.send_message`, `notifier.send_photo`, `notifier.msg_t3`, `find_manager`.
- Produces:

```python
def start_task(store, user: dict, id_viec: str) -> Result          # notified luôn True, không gửi gì
def submit_task(store, notifier, user: dict, id_viec: str, *, link: str | None = None,
                photo: bytes | None = None, photo_name: str | None = None, today: date) -> Result
```

- [ ] **Step 1: Viết test thất bại.** Mỗi test dựng `store` có sẵn một dòng `viec(Trang_Thai=...)`.

```python
@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_LAM_LAI])
def test_bat_dau(store, nv1, tu): ...          # → Trang_Thai == Đang làm

@pytest.mark.parametrize("tu", [c.TT_DANG_LAM, c.TT_CHO_DUYET, c.TT_HOAN_THANH])
def test_bat_dau_sai_trang_thai(store, nv1, tu): ...     # InvalidState, Sheet không đổi

def test_bat_dau_viec_nguoi_khac(store, nv2): ...        # PermissionDenied
def test_quan_ly_khong_bat_dau_ho(store, ql): ...        # PermissionDenied
def test_viec_khong_ton_tai(store, nv1):                 # Review Focus 4
    with pytest.raises(services.ServiceError, match="Không tìm thấy"): services.start_task(store, nv1, "V-khongco")

@pytest.mark.parametrize("tu", [c.TT_DANG_LAM, c.TT_LAM_LAI])
def test_bao_cao_bang_link(store, notifier, nv1, tu):
    r = services.submit_task(store, notifier, nv1, ID, link=" https://drive.google.com/x ", today=date(2026, 11, 22))
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_LINK], t[c.COL_NGAY_HOAN_THANH]) == (c.TT_CHO_DUYET, "https://drive.google.com/x", "2026-11-22")
    assert r.notified and notifier.sent[0][0] == "100" and "Nguyễn An" in notifier.sent[0][1]     # T3 tới quản lý

@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_CHO_DUYET, c.TT_HOAN_THANH])
def test_bao_cao_sai_trang_thai(store, notifier, nv1, tu): ...   # InvalidState; bấm hai lần rơi vào ca Chờ duyệt

@pytest.mark.parametrize("kw", [{}, {"link": ""}, {"link": "   "}, {"link": "drive.google.com/x"},
    {"link": "javascript:alert(1)"}, {"link": "https://a.vn", "photo": PNG}, {"photo": b""},
    {"photo": b"khong phai anh"}, {"photo": PNG + b"0" * c.ANH_MAX_BYTES}])
def test_chung_minh_khong_hop_le(store, notifier, nv1, kw): ...  # InvalidInput, Sheet không đổi, notifier.sent rỗng

def test_bao_cao_viec_nguoi_khac(store, notifier, nv2): ...      # PermissionDenied

def test_bao_cao_link_telegram_loi_van_luu(store, notifier, nv1):
    notifier.ok = False
    r = services.submit_task(store, notifier, nv1, ID, link="https://a.vn", today=D)
    assert r.notified is False and store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET

def test_bao_cao_bang_anh(store, notifier, nv1):
    r = services.submit_task(store, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert store.get_task(ID)[c.COL_LINK] == "tg:FILE123" and r.notified is True
    assert notifier.sent[0][0] == "100" and len(notifier.sent) == 1       # ảnh chính là T3, không gửi thêm tin

def test_anh_gui_loi_thi_khong_chuyen_trang_thai(store, notifier, nv1):
    notifier.ok = False
    with pytest.raises(services.ServiceError, match="link"): services.submit_task(store, notifier, nv1, ID, photo=PNG, photo_name="a.png", today=D)
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_DANG_LAM and store.get_task(ID)[c.COL_LINK] == ""

def test_quan_ly_chua_co_chat_id_thi_tu_choi_anh(nv1, notifier): ...      # store với QL01 chat "" → ServiceError nhắc dán link
```

`PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100`; ảnh JPG bắt đầu bằng `b"\xff\xd8\xff"`.

- [ ] **Step 2: Chạy** → FAIL `AttributeError: start_task`.
- [ ] **Step 3: Viết hai hàm.** Thứ tự trong mỗi hàm: `get_task` (đọc mới) → kiểm tra vai trò `NhanVien` và `Nguoi_Nhan == user[ID_NV]` → kiểm tra trạng thái → kiểm tra đầu vào → ghi → gửi tin. Link hợp lệ khi khớp `^https?://\S+$` sau `strip`. Ảnh hợp lệ khi có chữ ký PNG hoặc JPG và không quá `ANH_MAX_BYTES`. Phải có đúng một trong hai: link hoặc ảnh. Với ảnh: gửi `send_photo` tới chat quản lý với chú thích `msg_t3(task, ten_nv, None)`, có `file_id` rồi mới ghi `tg:<file_id>`.
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "services: bắt đầu và báo cáo hoàn thành, thông báo T3"`

---

### Task 9: `services.py`, `approve_task` và `return_task`

**Files:**
- Modify: `services.py`
- Test: `tests/test_services_quan_ly.py`

**Interfaces:**
- Consumes: `kpi.days_late`, `kpi.task_score`, `kpi.quarter_of`, `kpi.quarter_kpi`, `store.update_employee`, `notifier.msg_t4_duyet`, `notifier.msg_t4_tra_lai`.
- Produces:

```python
def approve_task(store, notifier, user: dict, id_viec: str, *, stars: int, today: date) -> Result
def return_task(store, notifier, user: dict, id_viec: str, *, ly_do: str) -> Result
```

- [ ] **Step 1: Viết test thất bại.** Dòng mặc định: `viec(Trang_Thai=Chờ duyệt, Han_Chot="2026-11-20", Ngay_Hoan_Thanh="2026-11-22", Link_Chung_Minh="https://a.vn")`.

```python
def test_duyet_ghi_sao_va_diem(store, notifier, ql):
    r = services.approve_task(store, notifier, ql, ID, stars=5, today=D)
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_SAO], t[c.COL_DIEM]) == (c.TT_HOAN_THANH, "5", "3.24")   # 3 × 0,90 × 1,2
    assert r.notified and notifier.sent[0][0] == "201"                                             # T4 tới nhân viên

def test_cho_duyet_lau_khong_bi_tinh_tre(store, notifier, ql): ...   # Ngay_Hoan_Thanh = Han_Chot, today sau 30 ngày → điểm "3.0" với 4 sao

def test_duyet_cap_nhat_kpi_quy_hien_tai(nv_store, notifier, ql):
    # NV01 có 4 việc quý 2026-Q4, trọng số 3, 5, 2, 4: hai việc Hoàn thành (2.5 và 1.2), việc 3 Chờ duyệt trễ 2 ngày, việc 4 Đang làm
    services.approve_task(nv_store, notifier, ql, "V-00000001", stars=5, today=D)
    assert nv_store.employees().iloc[1][c.COL_KPI_QUY] == "49.57"

def test_kpi_quy_chi_tinh_viec_cua_quy_hien_tai_va_cua_nguoi_do(...): ...  # thêm việc Hoàn thành của NV02 và của quý 2026-Q3 → vẫn "49.57"
def test_duyet_viec_quy_truoc_khi_quy_nay_chua_co_viec(...): ...           # KPI_Quy ghi "" (chưa có việc), không lỗi chia 0

@pytest.mark.parametrize("stars", [0, 6, None, 4.5, "5"])
def test_sao_khong_hop_le(store, notifier, ql, stars): ...      # InvalidInput, trạng thái vẫn Chờ duyệt

@pytest.mark.parametrize("tu", [c.TT_MOI_GIAO, c.TT_DANG_LAM, c.TT_LAM_LAI, c.TT_HOAN_THANH])
def test_duyet_sai_trang_thai(store, notifier, ql, tu): ...     # InvalidState

def test_duyet_hai_lan_khong_cong_doi(store, notifier, ql):     # Review Focus 4
    services.approve_task(store, notifier, ql, ID, stars=5, today=D)
    with pytest.raises(services.InvalidState): services.approve_task(store, notifier, ql, ID, stars=1, today=D)
    assert store.get_task(ID)[c.COL_DIEM] == "3.24" and len(notifier.sent) == 1

def test_nhan_vien_khong_tu_duyet(store, notifier, nv1): ...    # PermissionDenied cho cả approve và return

@pytest.mark.parametrize("cot, gia_tri", [(c.COL_NGAY_HOAN_THANH, ""), (c.COL_NGAY_HOAN_THANH, "22/11/2026"),
                                          (c.COL_HAN_CHOT, "46346"), (c.COL_TRONG_SO, "abc"), (c.COL_TRONG_SO, "")])
def test_o_bi_sua_tay_hong_thi_bao_ro_o_nao(notifier, ql, cot, gia_tri):     # Review Focus 1
    store = make_store(NHAN_SU, tasks=[viec_cho_duyet(**{cot: gia_tri})])
    with pytest.raises(services.ServiceError, match=cot): services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET

def test_ghi_kpi_quy_loi_thi_viec_van_duoc_duyet(store, notifier, ql, monkeypatch):
    monkeypatch.setattr(store, "update_employee", lambda *a, **k: (_ for _ in ()).throw(db.StoreError("x")))
    r = services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert r.kpi_saved is False and store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_HOAN_THANH

def test_tra_lai(store, notifier, ql):
    r = services.return_task(store, notifier, ql, ID, ly_do=" Thiếu số liệu ")
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_GHI_CHU_QL]) == (c.TT_LAM_LAI, "Thiếu số liệu")
    assert "Thiếu số liệu" in notifier.sent[0][1] and notifier.sent[0][0] == "201"

@pytest.mark.parametrize("ly_do", ["", "   "])
def test_tra_lai_thieu_ly_do(store, notifier, ql, ly_do): ...   # InvalidInput
def test_tra_lai_sai_trang_thai(...): ...                        # như test duyệt

def test_tra_lai_roi_nop_lai_tinh_tre_theo_lan_cuoi(store, notifier, ql, nv1):
    services.return_task(store, notifier, ql, ID, ly_do="Sửa lại")
    services.submit_task(store, notifier, nv1, ID, link="https://b.vn", today=date(2026, 11, 24))   # trễ 4 ngày
    services.approve_task(store, notifier, ql, ID, stars=4, today=D)
    assert store.get_task(ID)[c.COL_DIEM] == "2.4"                                                   # 3 × 0,80 × 1,0
```

- [ ] **Step 2: Chạy** → FAIL `AttributeError: approve_task`.
- [ ] **Step 3: Viết hai hàm.** `approve_task`: đọc mới → vai trò `QuanLy` → trạng thái → `stars` là `int` 1..5 → đọc `Han_Chot`, `Ngay_Hoan_Thanh` bằng `date.fromisoformat` và `Trong_So` bằng `int`, lỗi thì `ServiceError` nêu tên cột và `ID_Viec` → một lần `update_task` ghi cả `Trang_Thai`, `Danh_Gia_Sao`, `Diem_KPI_Nhan` → đọc lại `tasks()`, lọc theo `Nguoi_Nhan` và `Quy == kpi.quarter_of(today)`, tính `kpi.quarter_kpi`, ghi `KPI_Quy` (`""` khi `None`); lỗi `StoreError` ở bước này đặt `kpi_saved=False` chứ không ném → gửi T4. Điểm ghi vào Sheet dạng chuỗi của `float` (`"3.24"`, `"3.0"`).
- [ ] **Step 4: Chạy `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "services: duyệt, trả lại, cập nhật KPI_Quy, thông báo T4"`

---

### Task 10: `services.py`, các hàm đọc cho giao diện

**Files:**
- Modify: `services.py`
- Test: `tests/test_services_doc.py`

**Interfaces:**
- Produces:

```python
def kpi_table(tasks: pd.DataFrame, employees: pd.DataFrame, quy: str) -> pd.DataFrame
    # một dòng cho mỗi NhanVien; cột: ID_NV, Ten, "KPI" (float | None), "Hoan_Thanh" (int), "Tong_Viec" (int)
def employee_kpi(tasks: pd.DataFrame, id_nv: str, quy: str) -> tuple[float | None, int, int]
def overdue_tasks(tasks: pd.DataFrame, today: date) -> pd.DataFrame     # Han_Chot < today và trạng thái thuộc TT_CHUA_NOP
def status_counts(tasks: pd.DataFrame) -> dict[str, int]                # đủ 5 khóa theo config.TRANG_THAI, kể cả 0
def quarters(tasks: pd.DataFrame, today: date) -> list[str]             # các quý có việc cộng quý hiện tại, mới nhất trước
```

Tên ba cột `"KPI"`, `"Hoan_Thanh"`, `"Tong_Viec"` khai báo thêm trong `config.py` (`KQ_KPI`, `KQ_HOAN_THANH`, `KQ_TONG_VIEC`).

- [ ] **Step 1: Viết test thất bại**

```python
def test_kpi_table(nv_store_da_duyet):      # dữ liệu ví dụ spec: NV01 49.57 với 3/4 việc; NV02 chưa có việc
    b = services.kpi_table(tasks, employees, "2026-Q4").set_index(c.COL_ID_NV)
    assert list(b.index) == ["NV01", "NV02"]                    # không có dòng quản lý
    assert (b.loc["NV01", c.KQ_KPI], b.loc["NV01", c.KQ_HOAN_THANH], b.loc["NV01", c.KQ_TONG_VIEC]) == (49.57, 3, 4)
    assert b.loc["NV02", c.KQ_KPI] is None and b.loc["NV02", c.KQ_TONG_VIEC] == 0

def test_kpi_table_quy_khac_thi_trong(...): ...                 # "2026-Q3" → mọi KPI None
def test_employee_kpi(...): assert services.employee_kpi(tasks, "NV01", "2026-Q4") == (49.57, 3, 4)

def test_overdue(...):
    # hạn hôm qua + Đang làm → có; hạn hôm nay → không; hạn hôm qua + Chờ duyệt/Hoàn thành → không;
    # Han_Chot "abc" hoặc "" → bỏ qua, không lỗi (Review Focus 1)

def test_status_counts_du_5_khoa(): assert services.status_counts(bang_trong) == {t: 0 for t in c.TRANG_THAI}
def test_quarters(): assert services.quarters(tasks_q3_q4, date(2027, 1, 2)) == ["2027-Q1", "2026-Q4", "2026-Q3"]
```

- [ ] **Step 2: Chạy** → FAIL. **Step 3: Viết năm hàm**, tính KPI bằng `kpi.quarter_kpi` và `kpi.quarter_progress`. **Step 4: `pytest -v`** → PASS.
- [ ] **Step 5: Commit** `git commit -m "services: số liệu tổng quan, KPI theo nhân viên, việc quá hạn"`

---

### Task 11: `app.py`, đăng nhập và màn hình Nhân viên

**Files:**
- Create: `app.py`, `tests/test_app_nhan_vien.py`
- Modify: `tests/conftest.py` (fixture `app_env`, hàm `mo_app`, `dang_nhap`)

**Interfaces:**
- Consumes: `db.open_store`, `notifier.Notifier`, `auth.authenticate`, `auth.LoginGuard`, mọi hàm của `services`.
- Produces (khóa widget, các test và Task 12 dùng lại):
  - Đăng nhập: form `login_form`, `login_id`, `login_pin`, nút `login_submit`. Người dùng nằm ở `st.session_state["user"]`.
  - Thanh bên: nút `logout`, nút `refresh`.
  - Nhân viên, tab "Việc của tôi": nút `start_<ID_Viec>`; form `nop_form_<ID_Viec>` gồm `link_<ID_Viec>`, `anh_<ID_Viec>` (`st.file_uploader`, `type=["jpg", "jpeg", "png"]`), nút `nop_<ID_Viec>`.
  - Nhân viên, tab "KPI của tôi": `st.metric` nhãn "KPI quý" kèm dòng "x/y việc đã hoàn thành", hoặc dòng "Chưa có việc trong quý này".
- Fixture `app_env` trong `conftest.py`: monkeypatch `db.open_store` trả `store` giả, `notifier.Notifier` trả `FakeNotifier`, `services.hom_nay` trả `date(2026, 11, 11)`; gọi `st.cache_resource.clear()` và `st.cache_data.clear()` trước và sau test. `mo_app()` trả `AppTest.from_file("app.py", default_timeout=10)` đã gán `at.secrets["telegram_bot_token"]` và `at.secrets["sheet_id"]` giả rồi `.run()`. `dang_nhap(at, ident, pin)` điền form và bấm.

- [ ] **Step 1: Viết test thất bại**

```python
def test_chua_dang_nhap_chi_thay_form(app_env):
    at = mo_app()
    assert at.text_input(key="login_id") and len(at.tabs) == 0

def test_sai_pin_bao_loi_chung(app_env):
    at = mo_app(); dang_nhap(at, "NV01", "0000")
    assert at.error[0].value == c.MSG_DANG_NHAP_SAI and "user" not in at.session_state

def test_nhan_vien_chi_thay_viec_cua_minh(app_env):       # store có việc "Việc A" của NV01, "Việc B" của NV02
    at = mo_app(); dang_nhap(at, "NV01", "1234")
    noi_dung = " ".join(m.value for m in at.markdown)
    assert "Việc A" in noi_dung and "Việc B" not in noi_dung

def test_bat_dau_roi_bao_cao_bang_link(app_env):
    store, _ = app_env
    at = mo_app(); dang_nhap(at, "NV01", "1234")
    at.button(key="start_V-00000001").click().run()
    assert store.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_DANG_LAM
    at.text_input(key="link_V-00000001").set_value("https://a.vn")
    at.button(key="nop_V-00000001").click().run()
    assert store.get_task("V-00000001")[c.COL_TRANG_THAI] == c.TT_CHO_DUYET
    assert at.success[0].value == c.MSG_DA_LUU

def test_bao_cao_thieu_chung_minh_bao_loi_va_giu_form(app_env): ...   # at.error có nội dung; trạng thái không đổi
def test_telegram_loi_hien_canh_bao(app_env): ...                     # notifier.ok=False → at.warning[0].value == c.MSG_DA_LUU_CHUA_GUI
def test_viec_lam_lai_hien_ly_do(app_env): ...                        # Ghi_Chu_QL "Thiếu số liệu" xuất hiện trên trang
def test_kpi_cua_toi(app_env): ...                                    # at.metric[0].value == "49.57%"; có "3/4 việc đã hoàn thành"
def test_kpi_chua_co_viec(app_env): ...                               # thấy "Chưa có việc trong quý này", không có metric
def test_mat_ket_noi_sheet_hien_thong_bao(app_env): ...               # worksheet.fail_with → at.error chứa c.MSG_LOI_SHEET, không exception
def test_thieu_cot_hien_ten_cot(app_env): ...                         # at.error chứa tên cột thiếu
def test_dang_xuat(app_env): ...                                      # bấm logout → quay lại form đăng nhập
```

- [ ] **Step 2: Chạy** → FAIL (chưa có `app.py`).

- [ ] **Step 3: Viết `app.py` phần chung và phần Nhân viên.** Các lựa chọn đã chốt:
  - `get_store()`, `get_notifier()`, `get_guard()` bọc `st.cache_resource`, gọi `db.open_store(st.secrets)` và `notifier.Notifier(st.secrets["telegram_bot_token"])` qua thuộc tính module. `get_store()` gọi `check_headers()` một lần; `SchemaError` thì `st.error` rồi `st.stop()`.
  - Đọc bảng qua ba hàm bọc `st.cache_data(ttl=config.CACHE_TTL_GIAY)`. Nút `refresh` và mọi thao tác ghi thành công đều gọi `st.cache_data.clear()`.
  - Nhân viên chỉ nhận dữ liệu đã qua `services.visible_tasks`.
  - Mọi lời gọi `services.*` nằm trong một hàm bọc chung: `ServiceError` → `st.error(str(e))`; `StoreError` → `st.error(config.MSG_LOI_SHEET)`; thành công → lưu thông báo vào `st.session_state["flash"]` rồi `st.rerun()`; lần chạy sau hiện `st.success(MSG_DA_LUU)` hoặc `st.warning(MSG_DA_LUU_CHUA_GUI)`. Khi lỗi không `rerun`, nên giá trị trong form còn nguyên.
  - Form báo cáo hiện cả ô link và ô tải ảnh; kiểm tra "đúng một trong hai" do `services.submit_task` làm.
  - Thời điểm cho `authenticate`: `datetime.now(timezone.utc)`.
  - Việc nhóm theo trạng thái theo thứ tự `Làm lại`, `Mới giao`, `Đang làm`, `Chờ duyệt`, `Hoàn thành`.

- [ ] **Step 4: Chạy `pytest -v`** → PASS, kể cả `tests/test_quy_uoc.py` (giờ đã quét `app.py`).
- [ ] **Step 5: Commit** `git commit -m "app: đăng nhập và màn hình nhân viên"`

---

### Task 12: `app.py`, màn hình Quản lý và chuỗi đầy đủ

**Files:**
- Modify: `app.py`
- Test: `tests/test_app_quan_ly.py`, `tests/test_app_chuoi_day_du.py`

**Interfaces:**
- Produces (khóa widget):
  - Tab "Tổng quan": `tq_quy` (selectbox, mặc định quý hiện tại); năm `st.metric` theo trạng thái; `st.dataframe` và `st.bar_chart` KPI; bảng việc quá hạn.
  - Tab "Giao việc": `gv_mau` (selectbox, lựa chọn đầu là "(Gõ tay)"), `gv_ten`, `gv_mo_ta`, `gv_trong_so` (number_input 1..5), `gv_nguoi_nhan` (selectbox giá trị là `ID_NV`, hiển thị tên), `gv_han_chot` (date_input), nút `gv_submit`.
  - Tab "Chờ duyệt": với mỗi việc `sao_<ID>` (`st.radio` 1..5, nằm ngang, `index=None`), nút `duyet_<ID>`, `ly_do_<ID>`, nút `tra_<ID>`.
  - Tab "Tất cả công việc": `all_nv`, `all_tt`, `all_quy`, mỗi ô có lựa chọn "Tất cả".

- [ ] **Step 1: Viết test thất bại**

```python
# tests/test_app_quan_ly.py
def test_chon_mau_tu_dien(app_env):                      # mẫu M01: "Báo cáo tuần", "Gửi trước 17h thứ Sáu", trọng số 2
    at = mo_app(); dang_nhap(at, "QL01", "1111")
    at.selectbox(key="gv_mau").set_value("M01").run()
    assert at.text_input(key="gv_ten").value == "Báo cáo tuần" and at.number_input(key="gv_trong_so").value == 2

def test_sua_mau_sau_khi_giao_khong_doi_viec_cu(app_env): ...   # giao từ M01, đổi Trong_So_Diem của mẫu trong store → việc vẫn "2"
def test_giao_viec_thieu_ten_bao_loi_va_giu_o_nhap(app_env): ...  # at.error; gv_mo_ta còn nguyên giá trị
def test_duyet_chua_chon_sao_bao_loi(app_env): ...               # trạng thái vẫn Chờ duyệt
def test_tra_lai_thieu_ly_do_bao_loi(app_env): ...
def test_chung_minh_link_bam_duoc(app_env): ...                  # markdown chứa "(https://a.vn)"
def test_chung_minh_anh_hien_bang_bytes_khong_lo_token(app_env):
    # Link_Chung_Minh "tg:FILE123"; FakeNotifier.fetch_photo trả bytes PNG
    # → at.get("imgs") có 1 phần tử; không phần tử nào trên trang chứa "api.telegram.org" hay token
def test_anh_tai_khong_duoc_thi_bao(app_env): ...                # fetch_photo trả None → at.warning, vẫn duyệt được
def test_tong_quan(app_env): ...                                 # metric theo trạng thái đúng số; bảng KPI có NV01 49.57, NV02 "Chưa có việc"
def test_loc_tat_ca_cong_viec(app_env): ...                      # chọn all_nv = NV02 → bảng chỉ còn việc của NV02
def test_nhan_vien_khong_thay_tab_quan_ly(app_env): ...          # đăng nhập NV01 → không có widget key "gv_submit"
```

```python
# tests/test_app_chuoi_day_du.py
def test_dang_nhap_giao_bat_dau_bao_cao_duyet(app_env):
    store, notifier = app_env                             # store ban đầu không có việc
    at = mo_app(); dang_nhap(at, "QL01", "1111")
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
```

- [ ] **Step 2: Chạy** → FAIL.

- [ ] **Step 3: Viết phần Quản lý trong `app.py`.** Các lựa chọn đã chốt:
  - Tab "Giao việc" dùng widget thường (không `st.form`) để `gv_mau` có `on_change` điền `gv_ten`, `gv_mo_ta`, `gv_trong_so` qua `st.session_state`. Nút `gv_submit` dùng `on_click`: gọi `services.create_task`, thành công thì xóa các ô nhập trong callback, lỗi thì giữ nguyên.
  - Chứng minh: giá trị bắt đầu bằng `config.TG_PREFIX` thì gọi hàm `tai_anh(file_id)` bọc `st.cache_data` (gọi `get_notifier().fetch_photo`) và hiện bằng `st.image(<bytes>)`; ngược lại chỉ hiện thành link khi khớp `^https?://`, còn không thì hiện dạng `st.code`.
  - KPI `None` hiện "Chưa có việc". Cạnh mỗi KPI hiện "x/y việc đã hoàn thành".
  - Biểu đồ: `st.bar_chart` trên các nhân viên có KPI khác `None`.

- [ ] **Step 4: Chạy `pytest -v`** → PASS toàn bộ.
- [ ] **Step 5: Chạy thử bằng mắt** `streamlit run app.py` với `secrets.toml` thật nếu có; nếu chưa có thì ghi rõ trong báo cáo là bước này chưa làm.
- [ ] **Step 6: Commit** `git commit -m "app: màn hình quản lý và test chuỗi đầy đủ"`

---

### Task 13: Apps Script nhắc việc 8h, README, cập nhật CLAUDE.md

**Files:**
- Create: `apps_script/nhac_viec.gs`, `README.md`, `tests/test_apps_script.py`
- Modify: `CLAUDE.md` (mục "Trạng thái hiện tại")

**Interfaces:**
- Produces trong `nhac_viec.gs`:
  - `nhacViecHomNay()`: hàm gắn trigger. Đọc token từ `PropertiesService.getScriptProperties().getProperty("TELEGRAM_BOT_TOKEN")`.
  - `gomViecDenHan(dongViec, tieuDe, homNay)`: hàm thuần, trả `{ID_NV: [tên việc, ...]}` cho các việc có `Han_Chot == homNay` và trạng thái thuộc `Mới giao`, `Đang làm`, `Làm lại`.
  - `caiDatTrigger()`: tạo trigger hằng ngày khung 8h, xóa trigger cũ cùng tên trước khi tạo.

- [ ] **Step 1: Viết test thất bại**

```python
import pathlib, re, config as c
SRC = pathlib.Path("apps_script/nhac_viec.gs").read_text(encoding="utf-8")

def test_ten_bang_cot_trang_thai_khop_config():
    for chuoi in [c.SHEET_VIEC, c.SHEET_NHAN_SU, c.COL_HAN_CHOT, c.COL_TRANG_THAI, c.COL_NGUOI_NHAN,
                  c.COL_TEN_VIEC, c.COL_ID_NV, c.COL_CHAT_ID, c.TZ, *c.TT_CHUA_NOP]:
        assert f'"{chuoi}"' in SRC, chuoi

def test_khong_nhac_viec_da_nop():
    assert f'"{c.TT_CHO_DUYET}"' not in SRC and f'"{c.TT_HOAN_THANH}"' not in SRC

def test_khong_co_token_trong_ma():
    assert not re.search(r"\d{8,10}:[A-Za-z0-9_-]{30,}", SRC) and "TELEGRAM_BOT_TOKEN" in SRC
```

- [ ] **Step 2: Chạy** → FAIL `FileNotFoundError`.

- [ ] **Step 3: Viết `nhac_viec.gs`.** Đọc bằng `getDisplayValues()`, tra cột theo tên tiêu đề. "Hôm nay" = `Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM-dd")`. Mỗi người một tin liệt kê các việc đến hạn; người không có chat ID thì bỏ qua và `console.warn`. Gửi bằng `UrlFetchApp.fetch(..., {muteHttpExceptions: true})`; một người lỗi không chặn người sau. Đầu file có comment: tên bảng và cột phải khớp `config.py`.

- [ ] **Step 4: Chạy `pytest -v`** → PASS.

- [ ] **Step 5: Viết `README.md`** cho chủ dự án, bằng tiếng Việt, theo đúng thứ tự làm:
  1. Tạo file Google Sheet với ba bảng và đúng tiêu đề cột (chép từ `config.py`); đặt định dạng **Văn bản thuần** cho cột `SDT`, `Ma_PIN`, `Telegram_ChatID`, `Ngay_Giao`, `Han_Chot`, `Ngay_Hoan_Thanh`; nhập 6 dòng nhân sự với đúng một `QuanLy`.
  2. Tạo service account, bật Google Sheets API, chia sẻ file cho email service account quyền Editor. Không chia sẻ file cho nhân viên vì PIN nằm trong đó.
  3. Tạo bot bằng BotFather; từng người mở bot bấm Start; cách lấy chat ID.
  4. Điền `.streamlit/secrets.toml` từ file mẫu; chạy `pip install -r requirements.txt`, `pytest`, `streamlit run app.py`.
  5. Triển khai Streamlit Community Cloud từ repo private, dán Secrets, chọn đúng bản Python đã ghim.
  6. Cài Apps Script: dán `nhac_viec.gs`, đặt múi giờ dự án `Asia/Ho_Chi_Minh`, thêm Script Property `TELEGRAM_BOT_TOKEN`, chạy `caiDatTrigger()` một lần.
  7. Bảng kiểm tra cuối với Sheet và bot thật: đăng nhập, giao việc (T1), báo cáo bằng link và bằng ảnh (T3), duyệt và trả lại (T4), chạy tay `nhacViecHomNay()` (T2), xem `KPI_Quy` trên Sheet.
  8. Điều cần biết: app ngủ sau 12 giờ không ai vào; sửa/xóa việc làm thẳng trên Sheet và phải giữ định dạng ngày `YYYY-MM-DD`; bộ đếm khóa đăng nhập về 0 khi app khởi động lại; KPI giữa quý thấp vì việc chưa đến hạn vẫn nằm trong mẫu số.

- [ ] **Step 6: Sửa mục "Trạng thái hiện tại" và "Việc phải hỏi trước khi code" trong `CLAUDE.md`** cho đúng thực tế sau khi có code.

- [ ] **Step 7: Commit** `git commit -m "Apps Script nhắc việc 8h, README hướng dẫn cài đặt"`

---

## Đối chiếu với spec

| Mục spec | Task |
|---|---|
| 2. D1, D2 | 3 (`quarter_target`), 5 (`auth.py`), 9 (ghi `KPI_Quy`) |
| 4. Kiến trúc, phụ thuộc một chiều | Cấu trúc file; test quy ước ở Task 1 |
| 5. Dữ liệu, quy tắc ngày, SĐT, quý theo hạn chót | 1, 2, 4, 5, 7 |
| 6. Phân quyền, bảng chuyển trạng thái | 7, 8, 9 |
| 6. Đăng nhập, khóa 5 lần / 15 phút | 5, 11 |
| 7. Công thức và bảng ca kiểm thử | 2, 3 |
| 8. T1, T3, T4, ảnh chứng minh | 6, 7, 8, 9, 12 |
| 8. T2 Apps Script | 13 |
| 9. Giao diện | 10, 11, 12 |
| 10. Bí mật, cache 30 giây, tìm dòng lúc ghi, lỗi kết nối | 1, 4, 11 |
| 11. Kiểm thử | Mỗi task; chuỗi đầy đủ ở Task 12 |

## Điểm spec không nói, kế hoạch đã tự chọn

Chủ dự án xem và báo nếu muốn khác:

1. **Hạn chót trong quá khứ vẫn giao được.** Spec không cấm, và quản lý có thể cần ghi nhận việc đã phát sinh.
2. **"Việc quá hạn" ở tab Tổng quan** là việc đã qua hạn mà nhân viên chưa nộp (`Mới giao`, `Đang làm`, `Làm lại`). Việc đang `Chờ duyệt` không tính.
3. **`KPI_Quy` trên Sheet là KPI của quý hiện tại theo lịch**, kể cả khi việc vừa duyệt thuộc quý khác. Giao diện luôn tính KPI trực tiếp từ bảng việc, không đọc cột này.
4. **Ghi `KPI_Quy` lỗi không hủy việc duyệt.** Việc vẫn `Hoàn thành`, giao diện báo cột `KPI_Quy` chưa cập nhật.
5. **Nhập sai 5 lần với ID không tồn tại cũng bị khóa**, để thông báo khóa không tiết lộ ID nào có thật.
6. **Lý do trả lại được giữ nguyên** trên Sheet sau khi nhân viên nộp lại, và bị ghi đè ở lần trả lại sau.
7. **Tin Telegram là văn bản thuần**, không định dạng đậm nghiêng, để tên việc có ký tự đặc biệt không làm hỏng tin.
8. **Apps Script không có test tự động chạy logic**, chỉ có test đối chiếu tên bảng, cột, trạng thái với `config.py`. Logic T2 được kiểm tra tay theo README.
