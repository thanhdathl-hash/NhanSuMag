"""Đọc và ghi Google Sheets qua gspread.

Mọi ô đọc lên đều là chuỗi. Mọi lần ghi dùng chế độ RAW để Sheets không tự diễn giải
ngày tháng hay công thức.
"""
import google.auth.exceptions
import gspread
import pandas as pd
import requests
from gspread.utils import rowcol_to_a1

import config

_DOC_THO = "UNFORMATTED_VALUE"
_GHI_THO = "RAW"
_LOI_MANG = (gspread.exceptions.GSpreadException, requests.RequestException,
             google.auth.exceptions.GoogleAuthError, PermissionError)


class StoreError(Exception):
    """Lỗi khi làm việc với Google Sheets."""


class SchemaError(StoreError):
    """File Sheet thiếu bảng hoặc thiếu cột."""


class TaskNotFound(StoreError):
    """Không có dòng nào mang khóa cần tìm."""


def _loi(e: Exception) -> StoreError:
    """Đổi lỗi của gspread, mạng hay Google thành StoreError với thông điệp tiếng Việt đúng nguyên nhân."""
    ma = getattr(getattr(e, "response", None), "status_code", None)
    if isinstance(e, PermissionError) or ma == 403:
        return StoreError(config.MSG_LOI_QUYEN_SHEET)
    if isinstance(e, google.auth.exceptions.GoogleAuthError):
        return StoreError(config.MSG_LOI_XAC_THUC)
    return StoreError(config.MSG_LOI_SHEET)


def _chuoi(v) -> str:
    """Đổi giá trị ô sang chuỗi đã cắt khoảng trắng thừa; số nguyên dạng 3.0 thành "3"."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return "" if v is None else str(v).strip()


class SheetStore:
    def __init__(self, spreadsheet):
        self._spreadsheet = spreadsheet

    # --- nội bộ ---

    def _doc_tho(self, sheet: str) -> tuple[list[str], list[list[str]]]:
        """Trả về (tiêu đề, các dòng) của một bảng, mọi ô là chuỗi, mỗi dòng đủ độ dài tiêu đề."""
        try:
            values = self._spreadsheet.worksheet(sheet).get_values(value_render_option=_DOC_THO)
        except gspread.WorksheetNotFound as e:
            raise SchemaError(f"File Sheet thiếu bảng {sheet}") from e
        except _LOI_MANG as e:
            raise _loi(e) from e
        if not values:
            return [], []
        tieu_de = [_chuoi(x).strip() for x in values[0]]
        dong = []
        for row in values[1:]:
            row = [_chuoi(x) for x in row][:len(tieu_de)]
            dong.append(row + [""] * (len(tieu_de) - len(row)))
        return tieu_de, dong

    def _thieu(self, sheet: str, tieu_de: list[str]) -> list[str]:
        return sorted(set(config.SHEET_COLS[sheet]) - set(tieu_de))

    def _doc(self, sheet: str) -> pd.DataFrame:
        tieu_de, dong = self._doc_tho(sheet)
        thieu = self._thieu(sheet, tieu_de)
        if thieu:
            raise SchemaError(f"Bảng {sheet} thiếu cột: {', '.join(thieu)}")
        cols = config.SHEET_COLS[sheet]
        vi_tri = [tieu_de.index(k) for k in cols]
        return pd.DataFrame([[r[i] for i in vi_tri] for r in dong], columns=cols, dtype=str)

    def _sua(self, sheet: str, khoa: str, fields: dict) -> None:
        """Tìm dòng theo khóa ngay lúc ghi (không dùng số dòng đã cache) rồi cập nhật từng ô."""
        tieu_de, dong = self._doc_tho(sheet)
        cot_khoa = config.SHEET_KEY[sheet]
        thieu = [k for k in [cot_khoa, *fields] if k not in tieu_de]
        if thieu:
            raise SchemaError(f"Bảng {sheet} thiếu cột: {', '.join(sorted(thieu))}")
        i_khoa = tieu_de.index(cot_khoa)
        so_dong = next((i for i, r in enumerate(dong, start=2) if r[i_khoa] == khoa), None)
        if so_dong is None:
            raise TaskNotFound(f"Không tìm thấy {khoa} trong bảng {sheet}")
        data = [{"range": rowcol_to_a1(so_dong, tieu_de.index(k) + 1), "values": [[v]]}
                for k, v in fields.items()]
        try:
            self._spreadsheet.worksheet(sheet).batch_update(data, value_input_option=_GHI_THO)
        except _LOI_MANG as e:
            raise _loi(e) from e

    # --- công khai ---

    def check_headers(self) -> None:
        """Kiểm tra đủ bảng, đủ cột. Lỗi nêu đúng tên bảng và cột bị thiếu."""
        loi = []
        for sheet in config.SHEET_COLS:
            try:
                tieu_de, _ = self._doc_tho(sheet)
            except SchemaError as e:
                loi.append(str(e))
                continue
            thieu = self._thieu(sheet, tieu_de)
            if thieu:
                loi.append(f"Bảng {sheet} thiếu cột: {', '.join(thieu)}")
        if loi:
            raise SchemaError(". ".join(loi))

    def employees(self) -> pd.DataFrame:
        return self._doc(config.SHEET_NHAN_SU)

    def templates(self) -> pd.DataFrame:
        return self._doc(config.SHEET_MAU)

    def tasks(self) -> pd.DataFrame:
        return self._doc(config.SHEET_VIEC)

    def get_task(self, id_viec: str) -> dict | None:
        """Đọc mới một dòng việc từ Sheet. None nếu không có."""
        df = self.tasks()
        khop = df[df[config.COL_ID_VIEC] == id_viec]
        return None if khop.empty else khop.iloc[0].to_dict()

    def _them(self, sheet: str, dong: dict) -> None:
        tieu_de, _ = self._doc_tho(sheet)
        thieu = self._thieu(sheet, tieu_de)
        if thieu:
            raise SchemaError(f"Bảng {sheet} thiếu cột: {', '.join(thieu)}")
        values = [dong.get(k, "") for k in tieu_de]   # xếp theo thứ tự cột thật của Sheet
        try:
            self._spreadsheet.worksheet(sheet).append_row(values, value_input_option=_GHI_THO, table_range="A1")
        except _LOI_MANG as e:
            raise _loi(e) from e

    def _xoa(self, sheet: str, khoa: str) -> None:
        """Tìm dòng theo khóa ngay lúc xóa rồi xóa đúng một dòng."""
        tieu_de, dong = self._doc_tho(sheet)
        cot_khoa = config.SHEET_KEY[sheet]
        if cot_khoa not in tieu_de:
            raise SchemaError(f"Bảng {sheet} thiếu cột: {cot_khoa}")
        i_khoa = tieu_de.index(cot_khoa)
        so_dong = next((i for i, r in enumerate(dong, start=2) if r[i_khoa] == khoa), None)
        if so_dong is None:
            raise TaskNotFound(f"Không tìm thấy {khoa} trong bảng {sheet}")
        try:
            self._spreadsheet.worksheet(sheet).delete_rows(so_dong)
        except _LOI_MANG as e:
            raise _loi(e) from e

    def append_task(self, task: dict) -> None:
        self._them(config.SHEET_VIEC, task)

    # --- lịch trình cá nhân ---

    def personal(self) -> pd.DataFrame:
        return self._doc(config.SHEET_LICH)

    def get_personal(self, id_lich: str) -> dict | None:
        df = self.personal()
        khop = df[df[config.COL_ID_LICH] == id_lich]
        return None if khop.empty else khop.iloc[0].to_dict()

    def append_personal(self, muc: dict) -> None:
        self._them(config.SHEET_LICH, muc)

    def update_personal(self, id_lich: str, fields: dict) -> None:
        self._sua(config.SHEET_LICH, id_lich, fields)

    def delete_personal(self, id_lich: str) -> None:
        self._xoa(config.SHEET_LICH, id_lich)

    def update_task(self, id_viec: str, fields: dict) -> None:
        self._sua(config.SHEET_VIEC, id_viec, fields)

    def update_employee(self, id_nv: str, fields: dict) -> None:
        self._sua(config.SHEET_NHAN_SU, id_nv, fields)


def open_store(secrets) -> SheetStore:
    """Mở file Sheet bằng service account lấy từ secrets."""
    try:
        client = gspread.service_account_from_dict(dict(secrets["gcp_service_account"]))
        return SheetStore(client.open_by_key(secrets["sheet_id"]))
    except _LOI_MANG as e:
        raise _loi(e) from e
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        # thiếu khóa trong secrets hoặc private_key dán sai; không đưa nội dung lỗi ra ngoài
        raise StoreError(config.MSG_LOI_SECRETS) from e
