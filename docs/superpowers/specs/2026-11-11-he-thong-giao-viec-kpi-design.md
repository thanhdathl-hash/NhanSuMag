# Hệ thống Giao việc, Quản lý tiến độ và KPI quý: bản thiết kế

- Ngày viết: 2026-11-11
- Trạng thái: thiết kế đã chốt để bàn giao sang Claude Code. Chưa có code.
- Bước tiếp theo: lập kế hoạch triển khai từ bản này, rồi mới viết code.

## 1. Mục tiêu và phạm vi

Một quản lý giao việc cho 5 nhân viên, theo dõi tiến độ, nghiệm thu và chấm điểm, rồi tổng hợp thành KPI theo quý. Chi phí vận hành phải bằng 0: không thuê máy chủ, không mua license.

Trong phạm vi:

- Quản lý tạo việc từ mẫu hoặc gõ tay, nghiệm thu, chấm sao, xem tổng quan.
- Nhân viên đăng nhập, xem việc của mình, bấm "Bắt đầu" và "Báo cáo hoàn thành" kèm chứng minh.
- Tính KPI quý theo công thức ở mục 7.
- Thông báo Telegram ở bốn thời điểm (mục 8).

Ngoài phạm vi của bản đầu:

- Sửa hoặc xóa việc đã giao trong app. Khi cần, quản lý sửa thẳng trên Google Sheet.
- Nhiều quản lý, nhiều phòng ban.
- App di động riêng, chế độ offline.
- Nhắc việc quá hạn. Bản đầu chỉ nhắc việc đến hạn trong ngày.

## 2. Hai quyết định chưa được xác nhận riêng

Chủ dự án đã đồng ý chuyển sang Claude Code với các phương án đề xuất, nhưng chưa trả lời riêng hai câu dưới đây. Hãy hỏi lại một lần trước khi viết `kpi.quarter_target` và `auth`.

| Mã | Câu hỏi | Đang dùng | Phương án còn lại |
|---|---|---|---|
| D1 | "Tổng điểm mục tiêu quý" là gì? | A: tổng trọng số các việc được giao có hạn trong quý | B: số điểm cố định quản lý nhập ở cột `KPI_Quy` |
| D2 | Đăng nhập thế nào? | ID hoặc SĐT, cộng mã PIN | Chỉ ID hoặc SĐT |

Thiết kế cô lập hai quyết định này: D1 chỉ nằm trong một hàm (`kpi.quarter_target`), D2 chỉ nằm trong `auth.py`. Đổi phương án không chạm vào phần còn lại.

Hệ quả cần nói rõ với chủ dự án khi hỏi lại:

- D1-A không phản ánh khối lượng: người được giao ít việc vẫn có thể đạt 100%. D1-B phản ánh khối lượng, nhưng quản lý phải giao đủ việc thì nhân viên mới có thể đạt 100%.
- D2 không có PIN nghĩa là ai biết số điện thoại của đồng nghiệp sẽ vào được tài khoản người đó, và ai biết ID của quản lý sẽ duyệt và chấm sao được.

## 3. Nền tảng

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Dữ liệu | Google Sheets | Miễn phí, quản lý xem và sửa trực tiếp được |
| Giao diện | Streamlit trên Streamlit Community Cloud | Miễn phí, đăng nhập tùy biến được, KPI viết bằng Python |
| Thông báo tức thời | Telegram Bot API, gọi từ app | Miễn phí |
| Nhắc việc 8h | Google Apps Script gắn với file Sheet | Streamlit không tự chạy theo lịch và có thể đang ngủ |

AppSheet đã được cân nhắc và loại: chỉ miễn phí khi app ở dạng prototype (tối đa 10 người dùng thử), triển khai chính thức cần license theo người dùng; và đăng nhập bằng tài khoản Google chứ không phải ID/SĐT.

Giới hạn của Streamlit Community Cloud, theo tài liệu của Streamlit tại ngày viết:

- App không có truy cập trong 12 giờ sẽ ngủ. Người mở đầu tiên phải bấm đánh thức và chờ app khởi động lại.
- Mỗi tài khoản có một app private. Repo của dự án này nên để private.
- Bộ nhớ khoảng 1 GB, đủ cho 6 người dùng.

## 4. Kiến trúc

```
giao-viec-kpi/
├── app.py                  # Giao diện: đăng nhập, màn hình Quản lý, màn hình Nhân viên
├── config.py               # Tên bảng, tên cột, trạng thái, hệ số KPI, múi giờ
├── db.py                   # Đọc và ghi Google Sheets (gspread)
├── auth.py                 # Xác thực, giới hạn số lần nhập sai
├── services.py             # Các thao tác nghiệp vụ, kiểm tra quyền và trạng thái
├── kpi.py                  # Công thức KPI, hàm thuần, không I/O
├── notifier.py             # Telegram: gửi tin, gửi ảnh, tải ảnh
├── apps_script/nhac_viec.gs  # Nhắc việc 8h
├── tests/
├── requirements.txt
├── .streamlit/secrets.toml.example
├── .gitignore              # chặn .streamlit/secrets.toml
└── README.md               # Hướng dẫn cài đặt cho chủ dự án
```

Quan hệ phụ thuộc đi một chiều: `app.py` gọi `services.py` và `auth.py`; `services.py` gọi `db.py`, `kpi.py`, `notifier.py`; mọi module đọc hằng số từ `config.py`. `app.py` không ghi thẳng vào Sheet và không gọi Telegram.

Trách nhiệm từng phần:

- `config.py`: nơi duy nhất khai báo tên bảng, tên cột, tên trạng thái và các hệ số. Đổi tên một cột trên Sheet thì chỉ sửa ở đây.
- `db.py`: trả về DataFrame cho từng bảng, thêm dòng việc mới, cập nhật một dòng theo `ID_Viec`. Kiểm tra tiêu đề cột khi khởi động và báo đúng tên cột bị thiếu.
- `auth.py`: nhận ID hoặc SĐT và PIN, trả về người dùng hoặc lỗi.
- `services.py`: năm thao tác `create_task`, `start_task`, `submit_task`, `approve_task`, `return_task`. Mỗi thao tác nhận người dùng của phiên, đọc lại dòng việc mới nhất từ Sheet, kiểm tra quyền và trạng thái rồi mới ghi.
- `kpi.py`: `h1`, `h2`, `task_score`, `quarter_target`, `quarter_kpi`. Không đọc Sheet, không đọc đồng hồ.
- `notifier.py`: không ném lỗi ra ngoài; trả về thành công hay thất bại để giao diện báo cho người dùng.

## 5. Dữ liệu

Cột đánh dấu (+) là cột thêm so với mô tả ban đầu của chủ dự án.

### Danh_Sach_Nhan_Su

| Cột | Ghi chú |
|---|---|
| `ID_NV` | Khóa, ví dụ `NV01` |
| `Ten` | |
| `SDT` (+) | Lưu dạng văn bản để giữ số 0 đầu |
| `Ma_PIN` (+) | 4 đến 6 chữ số, do quản lý đặt (theo D2) |
| `Telegram_ChatID` | Lưu dạng văn bản |
| `Role` | `QuanLy` hoặc `NhanVien`. Có đúng một dòng `QuanLy` |
| `KPI_Quy` | Theo D1-A: app ghi KPI quý hiện tại vào đây sau mỗi lần duyệt |

### Thu_Vien_Mau

| Cột | Ghi chú |
|---|---|
| `ID_Mau` | Khóa |
| `Ten_Viec` | |
| `Mo_Ta` | |
| `Trong_So_Diem` | Số nguyên 1 đến 5 |

### Data_Giao_Viec

| Cột | Ghi chú |
|---|---|
| `ID_Viec` | `V-` cộng 8 ký tự hex ngẫu nhiên, sinh lúc tạo |
| `Ten_Viec` | |
| `Mo_Ta` (+) | Chép từ mẫu hoặc gõ tay |
| `Nguoi_Nhan` | `ID_NV` |
| `Trong_So` (+) | 1 đến 5. Chép từ mẫu lúc giao, nên sửa mẫu sau này không đổi điểm việc cũ; việc gõ tay nhập trực tiếp |
| `Ngay_Giao` | `YYYY-MM-DD` |
| `Han_Chot` | `YYYY-MM-DD` |
| `Trang_Thai` | `Mới giao`, `Đang làm`, `Chờ duyệt`, `Hoàn thành`, `Làm lại` |
| `Link_Chung_Minh` | URL `http(s)://...` hoặc `tg:<file_id>` (ảnh gửi qua Telegram) |
| `Ngay_Hoan_Thanh` (+) | Ngày nhân viên bấm "Báo cáo hoàn thành" lần gần nhất. Cần để tính số ngày trễ |
| `Danh_Gia_Sao` | 1 đến 5, quản lý chấm khi duyệt |
| `Diem_KPI_Nhan` | Điểm thực tế của việc, ghi khi duyệt |
| `Ghi_Chu_QL` (+) | Lý do trả lại |
| `Thang` | `YYYY-MM`, tính từ `Han_Chot` |
| `Quy` | `YYYY-Qn`, tính từ `Han_Chot`, ví dụ `2026-Q4` |

Quy tắc chung:

- Ngày lưu dạng chuỗi `YYYY-MM-DD` và ghi bằng chế độ không để Sheets tự diễn giải, tránh lệch định dạng theo ngôn ngữ của file.
- "Hôm nay" luôn tính theo múi giờ `Asia/Ho_Chi_Minh`. Máy chủ Streamlit Cloud không đảm bảo chạy theo giờ Việt Nam, nên không được dùng `date.today()` trần.
- Số điện thoại được chuẩn hóa trước khi so sánh: bỏ khoảng trắng và dấu chấm, đổi đầu `+84` thành `0`.
- Một việc thuộc quý nào là do `Han_Chot` quyết định, không phải ngày giao hay ngày hoàn thành.

## 6. Phân quyền và luồng trạng thái

Quản lý thấy toàn bộ dữ liệu. Nhân viên chỉ thấy các dòng có `Nguoi_Nhan` bằng `ID_NV` của mình; việc lọc diễn ra trước khi dữ liệu được đưa ra giao diện.

| Thao tác | Ai | Từ trạng thái | Sang | Điều kiện | Việc kèm theo |
|---|---|---|---|---|---|
| Tạo việc | Quản lý | (chưa có) | Mới giao | Có tên, người nhận, hạn chót, trọng số 1 đến 5 | Báo nhân viên (T1) |
| Bắt đầu | Nhân viên, đúng người nhận | Mới giao, Làm lại | Đang làm | | |
| Báo cáo hoàn thành | Nhân viên, đúng người nhận | Đang làm, Làm lại | Chờ duyệt | Bắt buộc có link hoặc ảnh | Ghi `Ngay_Hoan_Thanh` = hôm nay; báo quản lý (T3) |
| Duyệt | Quản lý | Chờ duyệt | Hoàn thành | Bắt buộc chấm 1 đến 5 sao | Ghi `Danh_Gia_Sao`, `Diem_KPI_Nhan`; cập nhật `KPI_Quy`; báo nhân viên (T4) |
| Trả lại | Quản lý | Chờ duyệt | Làm lại | Bắt buộc có lý do | Ghi `Ghi_Chu_QL`; báo nhân viên (T4) |

Mọi chuyển trạng thái khác đều bị từ chối. Việc kiểm tra nằm trong `services.py`, không dựa vào chuyện nút có hiện trên màn hình hay không: trước khi ghi, hàm đọc lại dòng việc từ Sheet để tránh bấm hai lần hoặc thao tác trên dữ liệu cũ.

Đăng nhập (theo D2):

- Người dùng nhập ID hoặc SĐT và mã PIN. So sánh PIN bằng `hmac.compare_digest`.
- Sai 5 lần liên tiếp cho cùng một tài khoản thì khóa tài khoản đó 15 phút. Bộ đếm nằm trong bộ nhớ của tiến trình (`st.cache_resource`), nên sẽ về 0 khi app khởi động lại.
- Phiên đăng nhập nằm trong `st.session_state`, mất khi đóng tab. Có nút đăng xuất.
- Thông báo lỗi không tiết lộ ID có tồn tại hay không.

## 7. Công thức KPI

```
Điểm thực tế của một việc = Trong_So × H1 × H2      (làm tròn 2 chữ số)
KPI quý (%) = Tổng điểm thực tế / Tổng điểm mục tiêu × 100
```

**H1, hệ số đúng hạn.** Gọi `d` là số ngày trễ: `Ngay_Hoan_Thanh` trừ `Han_Chot`, không nhỏ hơn 0. Khi đó `H1 = max(0,5; 1 − 0,05 × d)`. Xong sớm hoặc đúng hạn cho 1,0; trễ từ 10 ngày trở lên cho 0,5. Mốc tính là ngày nhân viên báo cáo, nên thời gian chờ quản lý duyệt không bị tính là trễ. Việc bị trả lại thì tính theo lần báo cáo cuối.

**H2, hệ số chất lượng.**

| Sao | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| H2 | 1,2 | 1,0 | 0,8 | 0,7 | 0,6 |

**Tổng điểm thực tế** là tổng `Diem_KPI_Nhan` của các việc `Hoàn thành` thuộc quý. Việc chưa hoàn thành được 0 điểm.

**Tổng điểm mục tiêu** (theo D1-A) là tổng `Trong_So` của mọi việc được giao cho nhân viên thuộc quý đó, ở bất kỳ trạng thái nào. 100% tương ứng với mọi việc đúng hạn và đạt 4 sao; mức cao nhất là 120%. Nếu nhân viên chưa có việc nào trong quý, giao diện hiện "chưa có việc" thay vì chia cho 0.

Một hệ quả dễ gây hiểu lầm: giữa quý, các việc chưa đến hạn vẫn nằm trong mẫu số, nên KPI tạm tính sẽ thấp cho tới khi việc được duyệt dần. Giao diện hiện kèm "x/y việc đã hoàn thành" bên cạnh con số KPI để người xem không đọc nhầm.

Bảng ca kiểm thử cho `kpi.py`:

| Trọng số | Ngày trễ | Sao | H1 | H2 | Điểm |
|---|---|---|---|---|---|
| 3 | 0 | 4 | 1,00 | 1,0 | 3,00 |
| 1 | 0 (xong sớm 3 ngày) | 5 | 1,00 | 1,2 | 1,20 |
| 3 | 2 | 5 | 0,90 | 1,2 | 3,24 |
| 4 | 1 | 3 | 0,95 | 0,8 | 3,04 |
| 4 | 9 | 2 | 0,55 | 0,7 | 1,54 |
| 5 | 10 | 4 | 0,50 | 1,0 | 2,50 |
| 5 | 30 | 4 | 0,50 | 1,0 | 2,50 |
| 2 | 0 | 1 | 1,00 | 0,6 | 1,20 |

Ví dụ KPI quý: một nhân viên có bốn việc trong quý với trọng số 3, 5, 2, 4 (mục tiêu 14). Ba việc đã duyệt được 3,24; 2,50; 1,20 điểm, việc trọng số 4 chưa xong. KPI = 6,94 / 14 × 100 = 49,57%.

## 8. Thông báo Telegram

| Mã | Khi nào | Gửi cho | Chạy ở đâu |
|---|---|---|---|
| T1 | Quản lý tạo việc | Nhân viên nhận việc | App |
| T2 | Khoảng 8h mỗi sáng | Nhân viên có việc đến hạn hôm nay | Apps Script |
| T3 | Nhân viên báo cáo hoàn thành | Quản lý | App |
| T4 | Quản lý duyệt hoặc trả lại | Nhân viên | App |

T4 không có trong yêu cầu ban đầu; được thêm vì nếu thiếu, nhân viên không biết việc bị trả lại.

Nguyên tắc cho T1, T3, T4: ghi Sheet trước, gửi Telegram sau. Gửi thất bại không hủy thao tác; giao diện báo "đã lưu nhưng chưa gửi được thông báo". Mỗi lần gọi có giới hạn thời gian 10 giây.

**Ảnh chứng minh.** Google Sheets không chứa được file ảnh, nên ảnh đi qua Telegram:

1. Nhân viên tải ảnh lên trong form báo cáo (JPG hoặc PNG, app giới hạn 5 MB).
2. App gửi ảnh tới chat của quản lý bằng `sendPhoto`, chú thích là nội dung T3.
3. App lấy `file_id` từ phản hồi và ghi `tg:<file_id>` vào `Link_Chung_Minh`.
4. Khi quản lý nghiệm thu, app gọi `getFile`, tải ảnh ở phía máy chủ rồi hiển thị. Token của bot không bao giờ được gửi xuống trình duyệt.

Với ảnh, bước 2 phải thành công thì mới chuyển trạng thái, vì Telegram là nơi duy nhất giữ ảnh. Nếu quản lý chưa có `Telegram_ChatID` hoặc gửi ảnh lỗi, app báo lỗi và đề nghị dán link thay thế. Khi triển khai, kiểm tra giới hạn kích thước hiện hành của Bot API cho `sendPhoto` và `getFile`.

**T2, Apps Script.** Script gắn với file Sheet, chạy bằng trigger theo thời gian mỗi ngày vào khung 8h, múi giờ của script đặt là `Asia/Ho_Chi_Minh`. Trigger loại này chạy trong khung giờ đã chọn chứ không đúng từng phút. Script đọc `Data_Giao_Viec`, lọc các việc có `Han_Chot` bằng hôm nay và trạng thái thuộc `Mới giao`, `Đang làm`, `Làm lại`, gom theo người nhận và gửi mỗi người một tin. Token của bot nằm trong Script Properties, không nằm trong mã.

Điều kiện để bot nhắn được: mỗi người phải mở bot và bấm Start một lần. README sẽ hướng dẫn cách lấy chat ID.

## 9. Giao diện

Màn hình đăng nhập: ô ID hoặc SĐT, ô PIN.

Quản lý, bốn tab:

- **Tổng quan:** số việc theo trạng thái, bảng và biểu đồ cột KPI quý theo nhân viên, danh sách việc quá hạn. Có ô chọn quý.
- **Giao việc:** chọn mẫu (tự điền tên, mô tả, trọng số) hoặc gõ tay; chọn người nhận và hạn chót.
- **Chờ duyệt:** từng việc kèm chứng minh (link bấm được hoặc ảnh), chấm sao và duyệt, hoặc trả lại kèm lý do.
- **Tất cả công việc:** bảng lọc theo nhân viên, trạng thái, quý.

Nhân viên, hai tab:

- **Việc của tôi:** nhóm theo trạng thái. Việc `Làm lại` hiện lý do của quản lý. Nút "Bắt đầu"; form "Báo cáo hoàn thành" với hai lựa chọn dán link hoặc tải ảnh.
- **KPI của tôi:** KPI quý hiện tại và số việc đã hoàn thành.

Toàn bộ giao diện bằng tiếng Việt.

## 10. Bí mật, triển khai và xử lý lỗi

- Bí mật nằm trong `.streamlit/secrets.toml` khi chạy máy cá nhân và trong mục Secrets của Streamlit Cloud khi triển khai: khóa service account của Google, ID của file Sheet, token bot Telegram. File này bị `.gitignore` chặn; repo chỉ chứa `secrets.toml.example`.
- File Sheet chỉ chia sẻ cho quản lý và email của service account (quyền Editor). Mã PIN nằm trong Sheet dạng văn bản thường, nên ai xem được Sheet là xem được PIN. Đây là rủi ro đã chấp nhận cho bản đầu; phương án thay thế là lưu PIN đã băm và thêm chức năng đổi PIN trong app.
- Đọc Sheet có cache ngắn (khoảng 30 giây) và nút "Làm mới". Sau mỗi lần ghi, cache bị xóa.
- Khi ghi, tìm dòng theo `ID_Viec` tại thời điểm ghi, không dùng số dòng đã cache.
- Lỗi kết nối Sheets hiện thông báo dễ hiểu và không làm mất dữ liệu người dùng vừa nhập trong form.

## 11. Kiểm thử

- `kpi.py`: pytest theo bảng ca ở mục 7, thêm ca mẫu số bằng 0.
- `services.py`: chạy với một lớp dữ liệu giả trong bộ nhớ. Kiểm tra từng dòng trong bảng chuyển trạng thái, và các ca bị từ chối: nhân viên thao tác trên việc của người khác, nhân viên tự duyệt, chuyển trạng thái sai thứ tự, báo cáo thiếu chứng minh.
- `auth.py`: đúng PIN, sai PIN, khóa sau 5 lần, chuẩn hóa SĐT.
- `notifier.py`: giả lập `requests`; lỗi mạng trả về thất bại chứ không ném lỗi.
- Luồng giao diện: `streamlit.testing.v1.AppTest` với lớp dữ liệu giả, đi hết chuỗi đăng nhập, giao việc, bắt đầu, báo cáo, duyệt.

Kiểm thử tự động không chạm vào Sheet thật và không gọi Telegram thật. Bước kiểm tra cuối với Sheet và bot thật do chủ dự án làm theo README.

## 12. Tài liệu tham khảo

- Streamlit Community Cloud, giới hạn và chế độ ngủ: https://docs.streamlit.io/streamlit-community-cloud/manage-your-app
- AppSheet, phạm vi miễn phí của prototype: https://discuss.google.dev/t/appsheet-pricing/159540
