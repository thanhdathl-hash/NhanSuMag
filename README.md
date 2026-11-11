# Hệ thống Giao việc và KPI quý

App nội bộ cho 1 quản lý và 5 nhân viên: giao việc, theo dõi tiến độ, nghiệm thu, chấm sao và tính KPI theo quý. Dữ liệu nằm trên Google Sheets, giao diện chạy trên Streamlit Community Cloud, thông báo đi qua Telegram. Không tốn chi phí vận hành.

Thiết kế chi tiết: `docs/superpowers/specs/2026-11-11-he-thong-giao-viec-kpi-design.md`.

Tài liệu này hướng dẫn chủ dự án cài đặt từ đầu. Làm theo đúng thứ tự.

## 1. Tạo file Google Sheet

Tạo một file Google Sheet mới với ba bảng (tab). Tên bảng và tên cột phải đúng từng ký tự; thứ tự cột không quan trọng.

**Bảng `Danh_Sach_Nhan_Su`**

| Cột | Ghi chú |
|---|---|
| `ID_NV` | Ví dụ `QL01`, `NV01` |
| `Ten` | Họ tên |
| `SDT` | Số điện thoại |
| `Ma_PIN` | 4 đến 6 chữ số, do quản lý đặt. Để trống thì người đó không đăng nhập được |
| `Telegram_ChatID` | Xem mục 3 |
| `Role` | `QuanLy` hoặc `NhanVien`. Phải có đúng một dòng `QuanLy` |
| `KPI_Quy` | Để trống. App tự ghi KPI quý hiện tại sau mỗi lần duyệt |

**Bảng `Thu_Vien_Mau`**: `ID_Mau`, `Ten_Viec`, `Mo_Ta`, `Trong_So_Diem` (số nguyên 1 đến 5).

**Bảng `Data_Giao_Viec`**: `ID_Viec`, `Ten_Viec`, `Mo_Ta`, `Nguoi_Nhan`, `Trong_So`, `Ngay_Giao`, `Han_Chot`, `Trang_Thai`, `Link_Chung_Minh`, `Ngay_Hoan_Thanh`, `Danh_Gia_Sao`, `Diem_KPI_Nhan`, `Ghi_Chu_QL`, `Thang`, `Quy`. Chỉ cần dòng tiêu đề, app tự thêm dòng khi giao việc.

**Quan trọng:** chọn các cột `SDT`, `Ma_PIN`, `Telegram_ChatID`, `Ngay_Giao`, `Han_Chot`, `Ngay_Hoan_Thanh` rồi vào Định dạng > Số > **Văn bản thuần túy**. Nếu không, Sheets sẽ bỏ số 0 đầu của số điện thoại và tự đổi định dạng ngày.

## 2. Tạo service account của Google

1. Vào Google Cloud Console, tạo một dự án, bật **Google Sheets API**.
2. Tạo một service account, tạo khóa dạng JSON và tải về. Giữ kín file này.
3. Mở file Sheet, bấm Chia sẻ, thêm email của service account với quyền **Người chỉnh sửa**.

Chỉ chia sẻ file Sheet cho quản lý và service account. **Không chia sẻ cho nhân viên**: mã PIN nằm trong Sheet dạng chữ thường, ai xem được Sheet là xem được PIN của mọi người.

## 3. Tạo bot Telegram

1. Trong Telegram, nhắn `@BotFather`, gõ `/newbot`, làm theo hướng dẫn để nhận token.
2. Từng người (quản lý và 5 nhân viên) mở bot vừa tạo và bấm **Start**. Bot không thể nhắn cho người chưa bấm Start.
3. Lấy chat ID của từng người: người đó nhắn `@userinfobot` và chép số ID nhận được vào cột `Telegram_ChatID`.

Ảnh chứng minh được gửi vào cuộc trò chuyện giữa quản lý và bot, nên quản lý bắt buộc phải có `Telegram_ChatID`.

## 4. Chạy trên máy cá nhân

Cần Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Mở `.streamlit/secrets.toml` và điền:

- `sheet_id`: đoạn nằm giữa `/d/` và `/edit` trong địa chỉ file Sheet.
- `telegram_bot_token`: token từ BotFather.
- `[gcp_service_account]`: chép từng trường từ file khóa JSON.

File `secrets.toml` đã bị `.gitignore` chặn. Không bao giờ commit file này, file khóa JSON hay token.

```bash
.venv/bin/pytest            # toàn bộ test, không chạm Sheet thật hay Telegram thật
.venv/bin/streamlit run app.py
```

## 5. Triển khai lên Streamlit Community Cloud

1. Giữ repo GitHub ở chế độ **private** (mỗi tài khoản Streamlit có một app private).
2. Vào share.streamlit.io, tạo app mới từ repo này, file chính `app.py`.
3. Trong Advanced settings, chọn **Python 3.12**. Các bản thư viện trong `requirements.txt` được ghim theo Python 3.12; nếu Streamlit Cloud không còn cung cấp 3.12 thì chọn bản gần nhất và chạy lại `pytest` trên bản đó trước.
4. Dán toàn bộ nội dung `secrets.toml` vào mục **Secrets**.

## 6. Nhắc việc 8h sáng

Streamlit không tự chạy theo lịch, nên việc nhắc do Google Apps Script đảm nhận.

1. Mở file Sheet, vào Tiện ích mở rộng > Apps Script.
2. Xóa mã mẫu, dán toàn bộ nội dung `apps_script/nhac_viec.gs`.
3. Vào Cài đặt dự án: đặt múi giờ `Asia/Ho_Chi_Minh`; ở Thuộc tính tập lệnh thêm `TELEGRAM_BOT_TOKEN` với giá trị là token bot.
4. Chọn hàm `caiDatTrigger`, bấm Chạy một lần và cấp quyền khi được hỏi.

Script chạy trong khung 8h đến 9h mỗi sáng (Google không đảm bảo đúng phút), gửi cho mỗi nhân viên một tin liệt kê việc đến hạn trong ngày mà chưa nộp. Bản đầu không nhắc việc đã quá hạn.

Nếu đổi tên bảng hoặc cột, phải sửa cả `config.py` lẫn đầu file `nhac_viec.gs`.

## 7. Kiểm tra cuối với Sheet và bot thật

Phần này chưa được kiểm thử tự động. Làm lần lượt và đánh dấu:

- [ ] Đăng nhập bằng ID và bằng số điện thoại. Nhập sai PIN 5 lần thì bị khóa 15 phút.
- [ ] Quản lý giao một việc từ mẫu và một việc gõ tay. Nhân viên nhận được tin Telegram.
- [ ] Nhân viên bấm Bắt đầu, rồi Báo cáo hoàn thành bằng link. Quản lý nhận được tin.
- [ ] Nhân viên báo cáo một việc khác bằng ảnh. Ảnh xuất hiện trong Telegram của quản lý và trong tab Chờ duyệt.
- [ ] Quản lý trả lại một việc kèm lý do. Nhân viên nhận tin và thấy lý do trong app.
- [ ] Quản lý chấm sao và duyệt. Nhân viên nhận tin; cột `Diem_KPI_Nhan` và `KPI_Quy` trên Sheet có số.
- [ ] Trong Apps Script, chạy tay `nhacViecHomNay` khi có một việc hạn hôm nay. Nhân viên nhận tin nhắc.
- [ ] Mở Sheet xem các cột ngày vẫn ở dạng `2026-11-20`.

## 8. Điều cần biết khi dùng

- **App ngủ sau 12 giờ không ai vào.** Người mở đầu tiên bấm nút đánh thức và chờ khoảng một phút.
- **Sửa hoặc xóa việc** làm thẳng trên Sheet, app không có chức năng này. Khi sửa ngày, giữ đúng dạng `YYYY-MM-DD`. Sau khi sửa, bấm "Làm mới dữ liệu" trong app (dữ liệu được nhớ tạm 30 giây).
- **Đổi hạn chót của một việc** thì sửa luôn cột `Thang` và `Quy` của dòng đó, vì việc thuộc quý nào là do hạn chót quyết định.
- **KPI giữa quý trông thấp** vì việc chưa đến hạn vẫn nằm trong mục tiêu. Con số tăng dần khi việc được duyệt. 100% tương ứng với mọi việc đúng hạn và đạt 4 sao; cao nhất là 120%.
- **Cột `KPI_Quy`** luôn là KPI của quý hiện tại theo lịch và chỉ được cập nhật khi có việc được duyệt. Con số trong app mới là số tính trực tiếp.
- **Khóa đăng nhập** được nhớ trong bộ nhớ của app, nên sẽ mất khi app khởi động lại.
- **Xóa một người khỏi bảng nhân sự** thì người đó bị đăng xuất ở lần tải trang kế tiếp.
- **Giới hạn ảnh** là 5 MB, JPG hoặc PNG. Khi triển khai nên kiểm tra lại giới hạn hiện hành của `sendPhoto` và `getFile` tại core.telegram.org/bots/api.

## Cấu trúc mã nguồn

```
app.py          Giao diện Streamlit
config.py       Tên bảng, tên cột, trạng thái, hệ số KPI, múi giờ
db.py           Đọc và ghi Google Sheets
auth.py         Xác thực
services.py     Thao tác nghiệp vụ, kiểm tra quyền và trạng thái
kpi.py          Công thức KPI
notifier.py     Telegram
apps_script/    nhac_viec.gs
tests/
```
