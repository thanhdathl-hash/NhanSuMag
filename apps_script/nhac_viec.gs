/**
 * Nhắc việc 8h sáng (T2): gửi Telegram cho nhân viên có việc đến hạn hôm nay.
 *
 * Script gắn với file Google Sheet (Tiện ích mở rộng > Apps Script).
 * Tên bảng, tên cột và tên trạng thái dưới đây PHẢI khớp với config.py của app.
 * Token của bot nằm trong Script Properties (khóa TELEGRAM_BOT_TOKEN), không nằm trong mã.
 * Cài đặt: xem README mục "Nhắc việc 8h".
 */

var MUI_GIO = "Asia/Ho_Chi_Minh";

var BANG_VIEC = "Data_Giao_Viec";
var BANG_NHAN_SU = "Danh_Sach_Nhan_Su";

var COT_TEN_VIEC = "Ten_Viec";
var COT_NGUOI_NHAN = "Nguoi_Nhan";
var COT_HAN_CHOT = "Han_Chot";
var COT_TRANG_THAI = "Trang_Thai";
var COT_ID_NV = "ID_NV";
var COT_CHAT_ID = "Telegram_ChatID";

// Chỉ nhắc việc nhân viên chưa nộp
var TRANG_THAI_CAN_NHAC = ["Mới giao", "Đang làm", "Làm lại"];

/**
 * Hàm thuần: gom tên các việc đến hạn hôm nay theo người nhận.
 * @param {string[][]} dongViec các dòng dữ liệu (không gồm tiêu đề)
 * @param {string[]} tieuDe dòng tiêu đề của bảng việc
 * @param {string} homNay ngày dạng yyyy-MM-dd
 * @return {Object<string, string[]>} ID_NV -> danh sách tên việc
 */
function gomViecDenHan(dongViec, tieuDe, homNay) {
  var iTen = tieuDe.indexOf(COT_TEN_VIEC);
  var iNguoi = tieuDe.indexOf(COT_NGUOI_NHAN);
  var iHan = tieuDe.indexOf(COT_HAN_CHOT);
  var iTrangThai = tieuDe.indexOf(COT_TRANG_THAI);
  if (iTen < 0 || iNguoi < 0 || iHan < 0 || iTrangThai < 0) {
    throw new Error("Bảng " + BANG_VIEC + " thiếu một trong các cột: " +
      [COT_TEN_VIEC, COT_NGUOI_NHAN, COT_HAN_CHOT, COT_TRANG_THAI].join(", "));
  }
  var ketQua = {};
  dongViec.forEach(function (dong) {
    var nguoi = String(dong[iNguoi] || "").trim();
    var han = String(dong[iHan] || "").trim();
    var trangThai = String(dong[iTrangThai] || "").trim();
    if (!nguoi || han !== homNay || TRANG_THAI_CAN_NHAC.indexOf(trangThai) < 0) {
      return;
    }
    if (!ketQua[nguoi]) {
      ketQua[nguoi] = [];
    }
    ketQua[nguoi].push(String(dong[iTen] || "").trim());
  });
  return ketQua;
}

/** Hàm gắn với trigger hằng ngày. Có thể bấm Chạy để thử bằng tay. */
function nhacViecHomNay() {
  var token = PropertiesService.getScriptProperties().getProperty("TELEGRAM_BOT_TOKEN");
  if (!token) {
    throw new Error("Chưa đặt Script Property TELEGRAM_BOT_TOKEN.");
  }
  var file = SpreadsheetApp.getActiveSpreadsheet();
  var homNay = Utilities.formatDate(new Date(), MUI_GIO, "yyyy-MM-dd");

  var viec = file.getSheetByName(BANG_VIEC).getDataRange().getDisplayValues();
  var theoNguoi = gomViecDenHan(viec.slice(1), viec[0], homNay);

  var nhanSu = file.getSheetByName(BANG_NHAN_SU).getDataRange().getDisplayValues();
  var iId = nhanSu[0].indexOf(COT_ID_NV);
  var iChat = nhanSu[0].indexOf(COT_CHAT_ID);
  var chatTheoId = {};
  nhanSu.slice(1).forEach(function (dong) {
    chatTheoId[String(dong[iId]).trim()] = String(dong[iChat]).trim();
  });

  Object.keys(theoNguoi).forEach(function (idNv) {
    var chatId = chatTheoId[idNv];
    if (!chatId) {
      console.warn("Bỏ qua " + idNv + ": chưa có " + COT_CHAT_ID);
      return;
    }
    var noiDung = "⏰ Hôm nay (" + homNay + ") bạn có " + theoNguoi[idNv].length + " việc đến hạn:\n" +
      theoNguoi[idNv].map(function (ten) { return "• " + ten; }).join("\n");
    try {
      var phanHoi = UrlFetchApp.fetch("https://api.telegram.org/bot" + token + "/sendMessage", {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify({ chat_id: chatId, text: noiDung.slice(0, 4096) }),
        muteHttpExceptions: true
      });
      if (phanHoi.getResponseCode() !== 200) {
        console.warn("Gửi cho " + idNv + " thất bại, mã " + phanHoi.getResponseCode());
      }
    } catch (e) {
      // Không in e.message vì có thể chứa URL kèm token; một người lỗi không chặn người sau
      console.warn("Gửi cho " + idNv + " thất bại do lỗi kết nối.");
    }
  });
}

/** Chạy MỘT lần để đặt lịch 8h sáng mỗi ngày. Chạy lại sẽ thay lịch cũ, không tạo trùng. */
function caiDatTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "nhacViecHomNay") {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger("nhacViecHomNay").timeBased().everyDays(1).atHour(8).inTimezone(MUI_GIO).create();
}
