"""Tạo file .streamlit/secrets.toml từ file khóa JSON của service account.

Cách dùng (Windows, trong thư mục dự án):

    .\\.venv\\Scripts\\python scripts\\tao_secrets.py "C:\\đường\\dẫn\\file-khoa.json"

Script hỏi thêm mã file Sheet (dán cả đường link cũng được) và token bot Telegram (bỏ trống nếu chưa có).
Khóa không được in ra màn hình. File secrets.toml đã bị .gitignore chặn, không bao giờ được commit.
"""
import getpass
import json
import pathlib
import re
import sys

DICH_MAC_DINH = pathlib.Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


def lay_sheet_id(gia_tri: str) -> str:
    """Nhận mã file Sheet hoặc cả đường link, trả về mã."""
    gia_tri = (gia_tri or "").strip()
    khop = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", gia_tri)
    return khop.group(1) if khop else gia_tri


def _chuoi(s: str) -> str:
    # Chuỗi JSON (có \n, \", \uXXXX) cũng là chuỗi TOML hợp lệ
    return json.dumps(s, ensure_ascii=True)


def tao_noi_dung(khoa: dict, sheet_id: str, token: str) -> str:
    if not isinstance(khoa, dict) or khoa.get("type") != "service_account" \
            or not khoa.get("private_key") or not khoa.get("client_email"):
        raise ValueError("File này không phải khóa JSON của service account. "
                         "Hãy tải lại ở Google Cloud: IAM > Service accounts > Keys > Add key > JSON.")
    sheet_id = lay_sheet_id(sheet_id)
    if not sheet_id:
        raise ValueError("Chưa có mã file Sheet.")
    dong = [
        "# Tạo bởi scripts/tao_secrets.py. KHÔNG commit, KHÔNG gửi file này cho ai.",
        f"sheet_id = {_chuoi(sheet_id)}",
        f"telegram_bot_token = {_chuoi((token or '').strip())}",
        "",
        "[gcp_service_account]",
    ]
    dong += [f"{k} = {_chuoi(str(v))}" for k, v in khoa.items()]
    return "\n".join(dong) + "\n"


def ghi(file_khoa, sheet_id: str, token: str, dich=DICH_MAC_DINH, ghi_de: bool = False) -> pathlib.Path:
    dich = pathlib.Path(dich)
    if dich.exists() and not ghi_de:
        raise FileExistsError(str(dich))
    khoa = json.loads(pathlib.Path(file_khoa).read_text(encoding="utf-8"))
    noi_dung = tao_noi_dung(khoa, sheet_id, token)
    dich.parent.mkdir(parents=True, exist_ok=True)
    dich.write_text(noi_dung, encoding="utf-8")
    return dich


def main() -> int:
    if len(sys.argv) != 2:
        print('Cách dùng: python scripts\\tao_secrets.py "đường\\dẫn\\file-khoa.json"')
        return 1
    file_khoa = pathlib.Path(sys.argv[1].strip('"'))
    if not file_khoa.is_file():
        print(f"Không thấy file: {file_khoa}")
        return 1
    sheet_id = input("Dán mã file Google Sheet (hoặc cả đường link): ")
    token = getpass.getpass("Dán token bot Telegram (bỏ trống rồi Enter nếu chưa có; chữ sẽ không hiện ra): ")
    ghi_de = False
    if DICH_MAC_DINH.exists():
        ghi_de = input(f"Đã có {DICH_MAC_DINH}. Ghi đè? (c/k): ").strip().lower() in ("c", "co", "có", "y")
        if not ghi_de:
            print("Không thay đổi gì.")
            return 1
    try:
        dich = ghi(file_khoa, sheet_id, token, ghi_de=ghi_de)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Lỗi: {e}")
        return 1
    print(f"Đã tạo {dich}")
    print("Giờ chạy: .\\.venv\\Scripts\\python -m streamlit run app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
