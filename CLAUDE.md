# Hệ thống Giao việc và KPI quý

App nội bộ cho 1 quản lý và 5 nhân viên: giao việc, theo dõi tiến độ, nghiệm thu, tính KPI theo quý. Chi phí vận hành phải bằng 0.

## Trạng thái hiện tại

Chưa có code. Thiết kế đã chốt trong spec:

`docs/superpowers/specs/2026-11-11-he-thong-giao-viec-kpi-design.md`

Spec là nguồn sự thật. Nếu yêu cầu mới mâu thuẫn với spec, sửa spec trước rồi mới sửa code.

Kế hoạch triển khai (13 task, TDD) đang chờ chủ dự án duyệt:

`docs/superpowers/plans/2026-11-11-he-thong-giao-viec-kpi.md`

Bước tiếp theo: chủ dự án duyệt kế hoạch, rồi viết code theo từng task.

## Quyết định đã xác nhận

Chủ dự án xác nhận ngày 2026-11-11, không cần hỏi lại:

- D1 = A: mục tiêu KPI quý là tổng trọng số việc được giao có hạn trong quý. App ghi KPI quý hiện tại vào cột `KPI_Quy` sau mỗi lần duyệt.
- D2: đăng nhập bằng ID hoặc SĐT cộng mã PIN.

## Stack

- Python 3.12, Streamlit, gspread, google-auth, pandas, requests, pytest.
- Dữ liệu: Google Sheets, truy cập bằng service account.
- Triển khai: Streamlit Community Cloud, repo GitHub private.
- Thông báo: Telegram Bot API. Nhắc việc 8h chạy bằng Google Apps Script gắn với file Sheet.

Ngày 2026-11-11 các bản sau cài được cùng nhau trên Python 3.13: streamlit 1.67.0, gspread 6.2.1, pandas 3.0.5. Kiểm tra lại phiên bản Python mà Streamlit Cloud hỗ trợ trước khi ghim trong `requirements.txt`.

## Cấu trúc

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

## Lệnh

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Quy ước

- Giao diện, thông báo và comment bằng tiếng Việt. Trao đổi với chủ dự án bằng tiếng Việt.
- Tên bảng, tên cột, tên trạng thái và hệ số chỉ khai báo trong `config.py`. Không viết chuỗi `"Chờ duyệt"` hay `"Han_Chot"` rải rác ở nơi khác.
- `kpi.py` chỉ gồm hàm thuần: không đọc Sheet, không đọc đồng hồ, nhận ngày qua tham số.
- `app.py` không ghi thẳng vào Sheet và không gọi Telegram. Mọi thao tác ghi đi qua `services.py`, nơi kiểm tra vai trò, chủ việc và trạng thái hiện tại.
- Ngày lưu dạng chuỗi `YYYY-MM-DD`. "Hôm nay" tính theo `Asia/Ho_Chi_Minh` bằng `zoneinfo`.
- Ghi Sheet trước, gửi Telegram sau. Telegram lỗi không được làm hỏng thao tác, trừ trường hợp ảnh chứng minh (xem spec mục 8).
- Token bot không bao giờ được đưa xuống trình duyệt, kể cả trong URL ảnh.
- Test không chạm vào Sheet thật và không gọi Telegram thật.

## Bí mật

Không commit `.streamlit/secrets.toml`, khóa service account, token bot hay ID file Sheet. Repo chỉ chứa `.streamlit/secrets.toml.example` với giá trị giả. Tạo `.gitignore` chặn `secrets.toml` trước commit code đầu tiên.

## Ngoài phạm vi

Sửa/xóa việc trong app, nhiều quản lý, app di động riêng, offline, nhắc việc quá hạn. Đừng thêm khi chưa được yêu cầu.
