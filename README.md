# Hệ thống Giao việc và KPI quý

App nội bộ cho 1 quản lý và 5 nhân viên: giao việc, theo dõi tiến độ, nghiệm thu, chấm sao và tính KPI theo quý. Dữ liệu nằm trên Google Sheets, giao diện chạy trên Streamlit Community Cloud, thông báo đi qua Telegram. Không tốn chi phí vận hành.

Thiết kế chi tiết: `docs/superpowers/specs/2026-11-11-he-thong-giao-viec-kpi-design.md`.

Tài liệu này hướng dẫn chủ dự án cài đặt từ đầu. Làm theo đúng thứ tự.

## Xem thử nhanh, chưa cần cài đặt gì

Muốn xem app trông thế nào trước khi tạo Sheet, service account và bot:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run demo.py
```

App mở với dữ liệu mẫu. Tài khoản: quản lý `QL01` PIN `1111`; nhân viên `NV01` đến `NV05` PIN `1234`. Mở hai tab trình duyệt để đăng nhập hai vai cùng lúc. Tin Telegram không được gửi đi mà hiện ở thanh bên trái.

Dữ liệu ở chế độ này nằm trong bộ nhớ và mất khi tắt app. Nó chỉ để xem; không thay được bước kiểm tra với Sheet và bot thật ở mục 8. Khi triển khai, file chính vẫn là `app.py`, không phải `demo.py`.

## 1. Tạo file Google Sheet

Tạo một file Google Sheet mới với bốn bảng (tab). Tên bảng và tên cột phải đúng từng ký tự; thứ tự cột không quan trọng.

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
| `Lich_Google` | Mã lịch Google của người đó, xem mục 6. Để trống thì app không đẩy sang Google Calendar |

**Bảng `Thu_Vien_Mau`**: `ID_Mau`, `Ten_Viec`, `Mo_Ta`, `Trong_So_Diem` (số nguyên 1 đến 5).

**Bảng `Data_Giao_Viec`**: `ID_Viec`, `Ten_Viec`, `Mo_Ta`, `Nguoi_Nhan`, `Trong_So`, `Ngay_Giao`, `Han_Chot`, `Trang_Thai`, `Link_Chung_Minh`, `Ngay_Hoan_Thanh`, `Danh_Gia_Sao`, `Diem_KPI_Nhan`, `Ghi_Chu_QL`, `Thang`, `Quy`, `Ghi_Chu_NV`. Chỉ cần dòng tiêu đề, app tự thêm dòng khi giao việc.

**Bảng `Lich_Ca_Nhan`** (lịch trình cá nhân): `ID_Lich`, `ID_NV`, `Noi_Dung`, `Ngay`, `Gio_Bat_Dau`, `Gio_Ket_Thuc`, `Lap`, `Lap_Den`, `Da_Xong`. Chỉ cần dòng tiêu đề, app tự thêm dòng.

**Quan trọng:** chọn các cột `SDT`, `Ma_PIN`, `Telegram_ChatID`, `Ngay_Giao`, `Han_Chot`, `Ngay_Hoan_Thanh` và toàn bộ bảng `Lich_Ca_Nhan` rồi vào Định dạng > Số > **Văn bản thuần túy**. Nếu không, Sheets sẽ bỏ số 0 đầu của số điện thoại và tự đổi định dạng ngày.

## 2. Tạo service account của Google

1. Vào Google Cloud Console, tạo một dự án, bật **Google Sheets API**. Nếu dùng tính năng Google Calendar (mục 6) thì bật thêm **Google Calendar API** trong cùng dự án.
2. Tạo một service account, tạo khóa dạng JSON và tải về. Giữ kín file này.
3. Mở file Sheet, bấm Chia sẻ, thêm email của service account với quyền **Người chỉnh sửa**.

Chỉ chia sẻ file Sheet cho quản lý và service account. **Không chia sẻ cho nhân viên**: mã PIN nằm trong Sheet dạng chữ thường, ai xem được Sheet là xem được PIN của mọi người.

## 3. Bot Telegram

Bot dùng để báo tin: nhân viên nhận tin khi được giao việc và khi việc được duyệt hoặc trả lại; quản lý nhận tin khi có việc chờ duyệt. Chưa có bot thì app vẫn chạy, chỉ không gửi tin và không báo cáo kèm ảnh được.

**Bước 1. Tạo bot (quản lý làm, một lần).** Trong Telegram, tìm `@BotFather` (có dấu tích xanh), gõ `/newbot`. Đặt tên hiển thị (ví dụ "Giao việc"), rồi đặt username kết thúc bằng `bot` (ví dụ `giaoviec_congty_bot`). BotFather trả về **token** dạng `123456789:AAH...`. Token là mật khẩu của bot: không gửi cho ai, không dán vào nhóm chat.

**Bước 2. Mọi người nhắn cho bot (mỗi người một lần).** Quản lý và từng nhân viên tìm username của bot, bấm **Start**, rồi gửi một tin bất kỳ, ví dụ "hi". Bot không nhắn được cho người chưa bấm Start.

**Bước 3. Lấy chat ID của từng người.** Ngay sau bước 2, mở trình duyệt, vào địa chỉ sau (thay `TOKEN` bằng token thật, giữ nguyên chữ `bot` phía trước):

```
https://api.telegram.org/botTOKEN/getUpdates
```

Trang hiện các tin mọi người vừa gửi. Với mỗi tin, tìm đoạn:

```
"chat":{"id":7012345678,"first_name":"Thảo","last_name":"Nguyễn", ...
```

Con số sau `"chat":{"id":` là chat ID của người đó (ở đây là `7012345678`). Nhận người bằng `first_name` và `last_name` (tên Telegram của họ). Bật "Pretty-print" ở đầu trang nếu trình duyệt có, cho dễ đọc.

- Trang chỉ hiện `{"ok":true,"result":[]}`: chưa ai nhắn, hoặc tin đã quá 24 giờ. Nhờ mọi người gửi lại một tin rồi tải lại trang.
- Báo `Unauthorized` hoặc `Not Found`: token dán sai hoặc thiếu chữ `bot` ngay trước token.
- Không dùng số ở mục `"from":{"id":...` của nhóm chat, hay số âm: đó không phải chat riêng với bot.

**Bước 4. Dán chat ID vào Sheet.** Mở bảng `Danh_Sach_Nhan_Su`, dán chat ID của từng người vào cột `Telegram_ChatID` **đúng dòng của người đó**, kể cả dòng quản lý. Chỉ dán con số, không dấu ngoặc kép, không khoảng trắng.

**Bước 5. Đưa token vào app.** Trên máy chạy app, chạy lại script tạo secrets (script hỏi ghi đè thì gõ `c`, hỏi token thì dán token, chữ sẽ không hiện ra khi dán):

```powershell
.\.venv\Scripts\python scripts\tao_secrets.py "đường\dẫn\file-khoa.json"
```

Khi đã triển khai lên Streamlit Cloud: vào app > Settings > Secrets, sửa dòng `telegram_bot_token = "..."` rồi bấm Save.

**Bước 6. Thử.** Tắt app (`Ctrl + C`) và chạy lại. Trong app bấm "Làm mới dữ liệu", rồi giao một việc thử cho một nhân viên: người đó phải nhận được tin "Việc mới" từ bot. Nếu app báo "Đã lưu nhưng chưa gửi được thông báo Telegram": kiểm tra chat ID của người đó, và người đó đã bấm Start chưa.

Ảnh chứng minh (không bắt buộc) được gửi vào cuộc trò chuyện giữa quản lý và bot, nên muốn báo cáo kèm ảnh thì dòng quản lý phải có `Telegram_ChatID`.

## 4. Chạy trên máy cá nhân

Cần Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Cách nhanh: để script tự tạo `secrets.toml` từ file khóa JSON (nó hỏi thêm mã file Sheet và token bot):

```powershell
.\.venv\Scripts\python scripts\tao_secrets.py "C:\đường\dẫn\file-khoa.json"
```

Hoặc tự làm: mở `.streamlit/secrets.toml` và điền:

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

## 6. Google Calendar (không bắt buộc)

Khi quản lý giao việc, app tự tạo một sự kiện vào ngày hạn chót trên lịch Google của người nhận. Lịch trình cá nhân thêm trong app cũng được đẩy sang đó. Ai không cài thì app vẫn chạy bình thường, chỉ là không có sự kiện bên Google.

Mỗi người tự làm một lần, trên máy tính (ứng dụng điện thoại không có đủ các mục này):

1. Mở calendar.google.com. Ở cột trái, bấm dấu **+** cạnh "Lịch khác" > **Tạo lịch mới**, đặt tên "Công việc", bấm Tạo lịch.
2. Mở cài đặt của lịch vừa tạo. Ở mục **Chia sẻ với những người cụ thể**, thêm email của service account (hỏi quản lý; email có dạng `...@...iam.gserviceaccount.com`) với quyền **Thay đổi sự kiện**.
3. Vẫn trong cài đặt đó, ở mục **Thông báo sự kiện cả ngày**, thêm một thông báo, ví dụ "1 ngày trước lúc 17:00". Đây là giờ Google nhắc hạn chót. App không đặt được giờ nhắc thay bạn.
4. Kéo xuống mục **Tích hợp lịch**, chép **Mã lịch** (dạng `...@group.calendar.google.com`) gửi cho quản lý.

Quản lý dán mã lịch của từng người vào cột `Lich_Google` của bảng nhân sự, rồi bấm "Làm mới dữ liệu" trong app.

Nên dùng lịch riêng như trên thay vì lịch chính: quyền "Thay đổi sự kiện" cho phép app đọc mọi sự kiện trên lịch được chia sẻ. Với lịch riêng, app chỉ thấy những gì chính nó tạo.

Điều cần biết:

- Sửa hạn chót trên Sheet sau khi giao thì sự kiện bên Google **không** tự đổi theo.
- Đánh dấu xong một mục cá nhân trong app không đổi gì bên Google. Xóa mục trong app thì sự kiện bên Google cũng bị xóa.
- Nếu app báo "Đã lưu nhưng chưa đồng bộ được với Google Calendar": kiểm tra mã lịch đúng chưa, lịch đã chia sẻ cho service account chưa, và Google Calendar API đã bật chưa.

## 7. Nhắc việc 8h sáng

Streamlit không tự chạy theo lịch, nên việc nhắc do Google Apps Script đảm nhận.

1. Mở file Sheet, vào Tiện ích mở rộng > Apps Script.
2. Xóa mã mẫu, dán toàn bộ nội dung `apps_script/nhac_viec.gs`.
3. Vào Cài đặt dự án: đặt múi giờ `Asia/Ho_Chi_Minh`; ở Thuộc tính tập lệnh thêm `TELEGRAM_BOT_TOKEN` với giá trị là token bot.
4. Chọn hàm `caiDatTrigger`, bấm Chạy một lần và cấp quyền khi được hỏi.

Script chạy trong khung 8h đến 9h mỗi sáng (Google không đảm bảo đúng phút), gửi cho mỗi nhân viên một tin liệt kê việc đến hạn trong ngày mà chưa nộp. Bản đầu không nhắc việc đã quá hạn.

Nếu đổi tên bảng hoặc cột, phải sửa cả `config.py` lẫn đầu file `nhac_viec.gs`.

## 8. Kiểm tra cuối với Sheet và bot thật

Phần này chưa được kiểm thử tự động. Làm lần lượt và đánh dấu:

- [ ] Đăng nhập bằng ID và bằng số điện thoại. Nhập sai PIN 5 lần thì bị khóa 15 phút.
- [ ] Quản lý giao một việc từ mẫu và một việc gõ tay. Nhân viên nhận được tin Telegram.
- [ ] Nhân viên bấm Bắt đầu, rồi Báo cáo hoàn thành kèm một dòng ghi chú. Quản lý nhận được tin có ghi chú.
- [ ] Nhân viên báo cáo một việc khác bằng ảnh. Ảnh xuất hiện trong Telegram của quản lý và trong tab Chờ duyệt.
- [ ] Quản lý trả lại một việc kèm lý do. Nhân viên nhận tin và thấy lý do trong app.
- [ ] Quản lý chấm sao và duyệt. Nhân viên nhận tin; cột `Diem_KPI_Nhan` và `KPI_Quy` trên Sheet có số.
- [ ] Trong Apps Script, chạy tay `nhacViecHomNay` khi có một việc hạn hôm nay. Nhân viên nhận tin nhắc.
- [ ] Mở Sheet xem các cột ngày vẫn ở dạng `2026-11-20`.
- [ ] Nếu đã cài mục 6: giao một việc cho người có `Lich_Google`, mở Google Calendar của người đó xem có sự kiện ở ngày hạn chót.
- [ ] Thêm một lịch trình cá nhân lặp hằng tuần có giờ. Nó hiện màu tím trên lịch trong app và hiện bên Google Calendar đúng giờ, đúng chuỗi lặp. Đánh dấu xong, rồi xóa; sự kiện bên Google biến mất.
- [ ] Đăng nhập bằng tài khoản quản lý: không thấy lịch trình cá nhân của nhân viên.

## 9. Điều cần biết khi dùng

- **App ngủ sau 12 giờ không ai vào.** Người mở đầu tiên bấm nút đánh thức và chờ khoảng một phút.
- **Sửa hoặc xóa việc** làm thẳng trên Sheet, app không có chức năng này. Khi sửa ngày, giữ đúng dạng `YYYY-MM-DD`. Sau khi sửa, bấm "Làm mới dữ liệu" trong app (dữ liệu được nhớ tạm 30 giây).
- **Việc thuộc quý nào là do hạn chót quyết định.** App tự tính quý từ cột `Han_Chot`, kể cả khi cột `Thang` và `Quy` trên Sheet để trống hoặc chưa sửa theo.
- **Thêm việc bằng tay trên Sheet** thì mỗi dòng phải có `ID_Viec` riêng, không trùng. Dòng thiếu mã hoặc trùng mã sẽ không dùng được, và app hiện cảnh báo cho quản lý.
- **Không giao được hai việc giống hệt nhau trong cùng một ngày** (cùng tên, người nhận, hạn chót) khi việc đầu chưa được bắt đầu. Đây là để chặn bấm nhầm hai lần; muốn giao thêm thì đổi tên việc.
- **KPI giữa quý trông thấp** vì việc chưa đến hạn vẫn nằm trong mục tiêu. Con số tăng dần khi việc được duyệt. 100% tương ứng với mọi việc đúng hạn và đạt 4 sao; cao nhất là 120%.
- **Cột `KPI_Quy`** luôn là KPI của quý hiện tại theo lịch và chỉ được cập nhật khi có việc được duyệt. Con số trong app mới là số tính trực tiếp.
- **Khóa đăng nhập** được nhớ trong bộ nhớ của app, nên sẽ mất khi app khởi động lại.
- **Xóa một người khỏi bảng nhân sự** thì người đó bị đăng xuất ở lần tải trang kế tiếp.
- **Lịch trình cá nhân** (việc nhỏ, sinh hoạt hằng ngày) thêm ở ô "Thêm lịch trình cá nhân" dưới lịch. Trong app chỉ người tạo thấy, quản lý cũng không thấy của nhân viên. Tuy vậy dữ liệu nằm trong bảng `Lich_Ca_Nhan` của file Sheet, nên ai mở được file (quản lý) vẫn đọc được: đừng ghi vào đó điều gì cần giữ kín. Mục cá nhân không tính vào KPI và không có nhắc qua Telegram. Không sửa được: muốn đổi thì xóa rồi thêm lại.
- **Giới hạn ảnh** là 5 MB, JPG hoặc PNG. Khi triển khai nên kiểm tra lại giới hạn hiện hành của `sendPhoto` và `getFile` tại core.telegram.org/bots/api.

## Cấu trúc mã nguồn

```
app.py          Giao diện Streamlit
demo.py         Chạy thử với dữ liệu mẫu trong bộ nhớ (không dùng để triển khai)
ui.py           Thẻ số liệu, lịch hạn chót và biểu đồ của bảng điều khiển
config.py       Tên bảng, tên cột, trạng thái, hệ số KPI, múi giờ
db.py           Đọc và ghi Google Sheets
auth.py         Xác thực
services.py     Thao tác nghiệp vụ, kiểm tra quyền và trạng thái
kpi.py          Công thức KPI
notifier.py     Telegram
scripts/        tao_secrets.py: tạo .streamlit/secrets.toml từ file khóa JSON
gcal.py         Google Calendar: tạo và xóa sự kiện
apps_script/    nhac_viec.gs
tests/
```
