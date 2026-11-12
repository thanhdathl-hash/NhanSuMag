"""Đồ giả cho test: gspread trong bộ nhớ và Telegram giả. Không chạm mạng."""
import gspread
from gspread.utils import a1_to_rowcol

import config as c
import db


class FakeWorksheet:
    """Giả lập gspread.Worksheet ở mức db.py cần dùng."""

    def __init__(self, rows):
        self.rows = [list(r) for r in rows]
        self.fail_with = None   # gán một Exception để giả lập mất mạng

    def _check(self):
        if self.fail_with is not None:
            raise self.fail_with

    def get_values(self, value_render_option=None):
        self._check()
        out = []
        for row in self.rows:
            row = list(row)
            while row and row[-1] == "":      # gspread thật cắt ô trống cuối dòng
                row.pop()
            out.append(row)
        while out and not out[-1]:
            out.pop()
        return out

    def append_row(self, values, value_input_option=None, table_range=None):
        self._check()
        assert value_input_option == "RAW"
        self.rows.append(list(values))

    def delete_rows(self, start_index, end_index=None):
        self._check()
        del self.rows[start_index - 1:(end_index or start_index)]

    def batch_update(self, data, value_input_option=None):
        self._check()
        assert value_input_option == "RAW"
        for item in data:
            row, col = a1_to_rowcol(item["range"])
            dong = self.rows[row - 1]
            while len(dong) < col:
                dong.append("")
            dong[col - 1] = item["values"][0][0]


class FakeSpreadsheet:
    def __init__(self, sheets):
        self.sheets = sheets

    def worksheet(self, name):
        if name not in self.sheets:
            raise gspread.WorksheetNotFound(name)
        return self.sheets[name]


def _bang(cols, dicts):
    return FakeWorksheet([list(cols)] + [[d.get(k, "") for k in cols] for d in dicts])


def make_store(employees, templates=(), tasks=(), personal=()):
    """SheetStore thật chạy trên gspread giả."""
    return db.SheetStore(FakeSpreadsheet({
        c.SHEET_NHAN_SU: _bang(c.NHAN_SU_COLS, employees),
        c.SHEET_MAU: _bang(c.MAU_COLS, templates),
        c.SHEET_VIEC: _bang(c.VIEC_COLS, tasks),
        c.SHEET_LICH: _bang(c.LICH_COLS, personal),
    }))


class FakeNotifier:
    """Ghi lại các lần gửi. Đặt ok=False để giả lập Telegram lỗi."""

    def __init__(self):
        self.ok = True
        self.sent = []          # (chat_id, nội dung hoặc chú thích)
        self.photo_bytes = None  # fetch_photo trả giá trị này

    def send_message(self, chat_id, text):
        if not chat_id or not self.ok:
            return False
        self.sent.append((chat_id, text))
        return True

    def send_photo(self, chat_id, photo, filename, caption):
        if not chat_id or not self.ok:
            return None
        self.sent.append((chat_id, caption))
        return "FILE123"

    def fetch_photo(self, file_id):
        return self.photo_bytes


class FakeCalendar:
    """Google Calendar giả: ghi lại sự kiện được tạo và bị xóa. Đặt ok=False để giả lập Google lỗi."""

    def __init__(self):
        self.ok = True
        self.events = []     # dict: calendar_id, ev_id, summary, description, ngay, gio_bat_dau, gio_ket_thuc, lap, lap_den
        self.deleted = []    # (calendar_id, ev_id)

    def add_event(self, calendar_id, ev_id, summary, description, ngay,
                  gio_bat_dau=None, gio_ket_thuc=None, lap=None, lap_den=None):
        if not calendar_id or not self.ok:
            return False
        self.events.append(dict(calendar_id=calendar_id, ev_id=ev_id, summary=summary, description=description,
                                ngay=ngay, gio_bat_dau=gio_bat_dau, gio_ket_thuc=gio_ket_thuc, lap=lap, lap_den=lap_den))
        return True

    def delete_event(self, calendar_id, ev_id):
        if not calendar_id or not self.ok:
            return False
        self.deleted.append((calendar_id, ev_id))
        return True
