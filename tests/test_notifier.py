from types import SimpleNamespace

import pytest
import requests

import notifier
from notifier import Notifier, msg_t1, msg_t3, msg_t4_duyet, msg_t4_tra_lai
from tests.conftest import viec

TOKEN = "123456:ABC-token-gia"


class GiaHttp:
    """Thay requests.post / requests.get: ghi lại lời gọi, trả lần lượt các phản hồi đã hẹn."""

    def __init__(self, *tra):
        self.calls = []
        self.tra = list(tra) or [{"ok": True, "result": {}}]

    def __call__(self, url, **kwargs):
        self.calls.append(SimpleNamespace(url=url, kwargs=kwargs))
        t = self.tra.pop(0) if len(self.tra) > 1 else self.tra[0]
        if isinstance(t, Exception):
            raise t
        return t if isinstance(t, PhanHoi) else PhanHoi(t)


class PhanHoi:
    def __init__(self, json=None, content=b"", status_code=200):
        self._json, self.content, self.status_code = json, content, status_code

    def json(self):
        if self._json is None:
            raise ValueError("không phải JSON")
        return self._json


@pytest.fixture
def gia_post(monkeypatch):
    g = GiaHttp()
    monkeypatch.setattr(requests, "post", g)
    return g


@pytest.fixture
def gia_get(monkeypatch):
    g = GiaHttp()
    monkeypatch.setattr(requests, "get", g)
    return g


def test_send_message_thanh_cong(gia_post):
    assert Notifier(TOKEN).send_message("201", "xin chào") is True
    goi = gia_post.calls[0]
    assert goi.url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert goi.kwargs["timeout"] == 10
    assert goi.kwargs["json"] == {"chat_id": "201", "text": "xin chào"}      # không parse_mode


@pytest.mark.parametrize("loi", [requests.ConnectionError("x"), requests.Timeout("x")])
def test_loi_mang_tra_that_bai_khong_nem(gia_post, gia_get, loi):
    gia_post.tra = [loi]
    gia_get.tra = [loi]
    assert Notifier(TOKEN).send_message("1", "a") is False
    assert Notifier(TOKEN).send_photo("1", b"x", "a.jpg", "c") is None
    assert Notifier(TOKEN).fetch_photo("f") is None


def test_telegram_tra_ok_false(gia_post):
    gia_post.tra = [{"ok": False, "description": "chat not found"}]
    assert Notifier(TOKEN).send_message("1", "a") is False
    assert Notifier(TOKEN).send_photo("1", b"x", "a.jpg", "c") is None


def test_phan_hoi_khong_phai_json(gia_post):
    gia_post.tra = [PhanHoi(json=None, status_code=502)]
    assert Notifier(TOKEN).send_message("1", "a") is False


def test_phan_hoi_thieu_truong(gia_post):
    gia_post.tra = [{"ok": True, "result": {"photo": []}}]
    assert Notifier(TOKEN).send_photo("1", b"x", "a.jpg", "c") is None


@pytest.mark.parametrize("chat_id", ["", "   ", None])
def test_chat_id_trong_khong_goi_mang(gia_post, chat_id):       # Review Focus 5
    assert Notifier(TOKEN).send_message(chat_id, "a") is False
    assert Notifier(TOKEN).send_photo(chat_id, b"x", "a.jpg", "c") is None
    assert gia_post.calls == []


def test_token_trong_khong_goi_mang(gia_post):
    assert Notifier("").send_message("1", "a") is False and gia_post.calls == []


def test_cat_tin_va_chu_thich_qua_dai(gia_post):               # Review Focus 5
    Notifier(TOKEN).send_message("1", "a" * 5000)
    assert len(gia_post.calls[0].kwargs["json"]["text"]) == 4096
    Notifier(TOKEN).send_photo("1", b"x", "a.jpg", "b" * 2000)
    assert len(gia_post.calls[1].kwargs["data"]["caption"]) == 1024


def test_send_photo_tra_file_id_anh_lon_nhat(gia_post):
    gia_post.tra = [{"ok": True, "result": {"photo": [{"file_id": "nho"}, {"file_id": "lon"}]}}]
    assert Notifier(TOKEN).send_photo("100", b"\xff\xd8", "a.jpg", "chú thích") == "lon"
    goi = gia_post.calls[0]
    assert goi.url.endswith("/sendPhoto") and goi.kwargs["timeout"] == 10
    assert goi.kwargs["files"]["photo"] == ("a.jpg", b"\xff\xd8")
    assert goi.kwargs["data"] == {"chat_id": "100", "caption": "chú thích"}


def test_fetch_photo(gia_get):
    gia_get.tra = [{"ok": True, "result": {"file_path": "photos/a.jpg"}}, PhanHoi(content=b"ANH")]
    assert Notifier(TOKEN).fetch_photo("lon") == b"ANH"
    assert gia_get.calls[0].url == f"https://api.telegram.org/bot{TOKEN}/getFile"
    assert gia_get.calls[0].kwargs["params"] == {"file_id": "lon"}
    assert gia_get.calls[1].url == f"https://api.telegram.org/file/bot{TOKEN}/photos/a.jpg"
    assert all(g.kwargs["timeout"] == 10 for g in gia_get.calls)


def test_fetch_photo_getfile_loi_tra_none(gia_get):
    gia_get.tra = [{"ok": False}]
    assert Notifier(TOKEN).fetch_photo("lon") is None


def test_fetch_photo_tai_ve_404_tra_none(gia_get):
    gia_get.tra = [{"ok": True, "result": {"file_path": "photos/a.jpg"}}, PhanHoi(content=b"loi", status_code=404)]
    assert Notifier(TOKEN).fetch_photo("lon") is None


def test_noi_dung_tin():
    v = viec(Ten_Viec="Báo cáo tuần", Mo_Ta="Gửi trước 17h")
    assert all(x in msg_t1(v) for x in ["Báo cáo tuần", "2026-11-20", "3", "Gửi trước 17h"])
    t3 = msg_t3(v, "Nguyễn An", "https://a.vn")
    assert all(x in t3 for x in ["Nguyễn An", "Báo cáo tuần", "V-00000001", "https://a.vn", "2026-11-20"])
    assert "None" not in msg_t3(v, "Nguyễn An", None)
    assert all(x in msg_t4_duyet(v, 5, 3.6) for x in ["Báo cáo tuần", "5", "3.6"])
    assert "Thiếu số liệu" in msg_t4_tra_lai(v, "Thiếu số liệu") and "Báo cáo tuần" in msg_t4_tra_lai(v, "x")


def test_module_khong_log_token():
    assert not hasattr(notifier, "logging")
