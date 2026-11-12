"""scripts/tao_secrets.py: tạo .streamlit/secrets.toml từ file khóa JSON của service account."""
import json
import tomllib

import pytest

from scripts import tao_secrets

KHOA = {
    "type": "service_account",
    "project_id": "du-an-gia",
    "private_key_id": "abc123",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE\"gia\\\n-----END PRIVATE KEY-----\n",
    "client_email": "app@du-an-gia.iam.gserviceaccount.com",
    "client_id": "123",
    "token_uri": "https://oauth2.googleapis.com/token",
    "universe_domain": "googleapis.com",
}


def test_noi_dung_doc_lai_dung_tung_truong():
    doc = tomllib.loads(tao_secrets.tao_noi_dung(KHOA, "ID_SHEET_GIA", "123:tokengia"))
    assert doc["sheet_id"] == "ID_SHEET_GIA" and doc["telegram_bot_token"] == "123:tokengia"
    assert doc["gcp_service_account"] == KHOA            # khóa bí mật giữ nguyên từng ký tự


def test_chua_co_token_thi_de_trong():
    assert tomllib.loads(tao_secrets.tao_noi_dung(KHOA, "x", ""))["telegram_bot_token"] == ""


@pytest.mark.parametrize("hong", [{}, {"type": "authorized_user"}, {**KHOA, "private_key": ""}, {**KHOA, "client_email": ""}])
def test_file_khong_phai_khoa_service_account_bi_tu_choi(hong):
    with pytest.raises(ValueError):
        tao_secrets.tao_noi_dung(hong, "x", "")


def test_thieu_sheet_id_bi_tu_choi():
    with pytest.raises(ValueError):
        tao_secrets.tao_noi_dung(KHOA, "  ", "")


def test_sheet_id_dan_ca_duong_link_van_lay_dung_ma():
    link = "https://docs.google.com/spreadsheets/d/1AbC_dEf-123/edit?usp=sharing"
    assert tao_secrets.lay_sheet_id(link) == "1AbC_dEf-123"
    assert tao_secrets.lay_sheet_id(" 1AbC_dEf-123 ") == "1AbC_dEf-123"


def test_ghi_file_khong_ghi_de_khi_da_co(tmp_path):
    f = tmp_path / "khoa.json"
    f.write_text(json.dumps(KHOA), encoding="utf-8")
    dich = tmp_path / ".streamlit" / "secrets.toml"
    tao_secrets.ghi(f, "ID", "", dich)
    assert tomllib.loads(dich.read_text(encoding="utf-8"))["sheet_id"] == "ID"
    with pytest.raises(FileExistsError):
        tao_secrets.ghi(f, "ID2", "", dich)
    tao_secrets.ghi(f, "ID2", "", dich, ghi_de=True)
    assert tomllib.loads(dich.read_text(encoding="utf-8"))["sheet_id"] == "ID2"
