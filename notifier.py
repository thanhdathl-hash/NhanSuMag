"""Telegram: gửi tin, gửi ảnh, tải ảnh. Không ném lỗi ra ngoài, chỉ trả thành công hay thất bại.

Token của bot chỉ nằm trong tiến trình máy chủ: không ghi log, không đưa vào thông báo lỗi.
"""
import requests

import config

_API = "https://api.telegram.org"
_LOI = (requests.RequestException, ValueError, KeyError, IndexError, TypeError)


class Notifier:
    def __init__(self, token: str):
        self._token = (token or "").strip()

    def _goi(self, method: str, **kwargs) -> dict | None:
        """Gọi một phương thức POST của Bot API, trả `result` hoặc None khi lỗi."""
        try:
            r = requests.post(f"{_API}/bot{self._token}/{method}", timeout=config.TELEGRAM_TIMEOUT, **kwargs)
            body = r.json()
            return body["result"] if body.get("ok") else None
        except _LOI:
            return None

    def _du_dieu_kien(self, chat_id) -> bool:
        return bool(self._token) and bool(str(chat_id or "").strip())

    def send_message(self, chat_id: str, text: str) -> bool:
        if not self._du_dieu_kien(chat_id):
            return False
        payload = {"chat_id": str(chat_id).strip(), "text": text[:config.TG_TEXT_MAX]}
        return self._goi("sendMessage", json=payload) is not None

    def send_photo(self, chat_id: str, photo: bytes, filename: str, caption: str) -> str | None:
        """Gửi ảnh, trả file_id của bản lớn nhất để lưu lại; None khi thất bại."""
        if not self._du_dieu_kien(chat_id):
            return None
        result = self._goi(
            "sendPhoto",
            data={"chat_id": str(chat_id).strip(), "caption": caption[:config.TG_CAPTION_MAX]},
            files={"photo": (filename, photo)},
        )
        try:
            return result["photo"][-1]["file_id"]
        except _LOI:
            return None

    def fetch_photo(self, file_id: str) -> bytes | None:
        """Tải ảnh về phía máy chủ để hiển thị. Trình duyệt không bao giờ thấy URL chứa token."""
        if not self._token or not file_id:
            return None
        try:
            r = requests.get(f"{_API}/bot{self._token}/getFile", params={"file_id": file_id},
                             timeout=config.TELEGRAM_TIMEOUT)
            body = r.json()
            if not body.get("ok"):
                return None
            tep = requests.get(f"{_API}/file/bot{self._token}/{body['result']['file_path']}",
                               timeout=config.TELEGRAM_TIMEOUT)
            return tep.content if tep.status_code == 200 else None
        except _LOI:
            return None


# --- Nội dung tin: văn bản thuần, không parse_mode ---

def msg_t1(task: dict) -> str:
    dong = [
        f"📌 Việc mới: {task[config.COL_TEN_VIEC]}",
        f"Hạn chót: {task[config.COL_HAN_CHOT]}",
        f"Trọng số: {task[config.COL_TRONG_SO]}",
    ]
    if task.get(config.COL_MO_TA):
        dong.append(f"Mô tả: {task[config.COL_MO_TA]}")
    return "\n".join(dong)


def msg_t3(task: dict, ten_nv: str, link: str | None) -> str:
    dong = [
        f"✅ {ten_nv} báo cáo hoàn thành: {task[config.COL_TEN_VIEC]} ({task[config.COL_ID_VIEC]})",
        f"Hạn chót: {task[config.COL_HAN_CHOT]}",
    ]
    if link:
        dong.append(f"Chứng minh: {link}")
    dong.append("Mở app để nghiệm thu.")
    return "\n".join(dong)


def msg_t4_duyet(task: dict, stars: int, diem: float) -> str:
    return f"🎉 Việc \"{task[config.COL_TEN_VIEC]}\" đã được duyệt: {stars} sao, {diem} điểm."


def msg_t4_tra_lai(task: dict, ly_do: str) -> str:
    return f"↩️ Việc \"{task[config.COL_TEN_VIEC]}\" bị trả lại.\nLý do: {ly_do}\nMở app để làm lại và báo cáo."
