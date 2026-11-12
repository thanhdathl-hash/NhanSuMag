import config


def test_nam_trang_thai_dung_thu_tu_spec():
    assert config.TRANG_THAI == ["Mới giao", "Đang làm", "Chờ duyệt", "Hoàn thành", "Làm lại"]


def test_h2_theo_bang_spec():
    assert config.H2_THEO_SAO == {5: 1.2, 4: 1.0, 3: 0.8, 2: 0.7, 1: 0.6}


def test_cot_bang_viec_dung_thu_tu_spec():
    assert config.VIEC_COLS == [
        "ID_Viec", "Ten_Viec", "Mo_Ta", "Nguoi_Nhan", "Trong_So",
        "Ngay_Giao", "Han_Chot", "Trang_Thai", "Link_Chung_Minh", "Ngay_Hoan_Thanh",
        "Danh_Gia_Sao", "Diem_KPI_Nhan", "Ghi_Chu_QL", "Thang", "Quy",
    ]


def test_cot_nhan_su_va_mau():
    assert config.NHAN_SU_COLS == ["ID_NV", "Ten", "SDT", "Ma_PIN", "Telegram_ChatID", "Role", "KPI_Quy", "Lich_Google"]
    assert config.MAU_COLS == ["ID_Mau", "Ten_Viec", "Mo_Ta", "Trong_So_Diem"]
