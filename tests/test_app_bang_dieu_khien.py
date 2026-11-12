import config as c
from tests.conftest import NHAN_SU, dang_nhap, html_tren_trang, mo_app, viec, viec_vi_du_spec

# "Hôm nay" trong app_env là 2026-11-11
VIEC = [
    viec(ID_Viec="V-1", Ten_Viec="Việc của An tháng 11", Han_Chot="2026-11-20", Trang_Thai=c.TT_DANG_LAM),
    viec(ID_Viec="V-2", Ten_Viec="Việc của Bình quá hạn", Han_Chot="2026-11-05", Nguoi_Nhan="NV02"),
    viec(ID_Viec="V-3", Ten_Viec="Việc của An tháng 12", Han_Chot="2026-12-03"),
    viec(ID_Viec="V-4", Ten_Viec="Việc quý sau", Han_Chot="2027-01-10"),
]


def test_quan_ly_thay_lich_thang_hien_tai_kem_ten_nguoi(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception
    lich = html_tren_trang(at)
    assert "Việc của An tháng 11" in lich and "Nguyễn An" in lich
    assert "Việc của Bình quá hạn" in lich and f"gv-viec gv-{c.NHOM_QUA_HAN}" in lich
    assert "Việc của An tháng 12" not in lich
    assert any("Tháng 11/2026" in s.value for s in at.subheader)
    assert lich.count('<td class="gv-hom-nay">') == 1 and 'class="gv-chu-giai"' in lich


def test_chuyen_thang(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    at.button(key="lich_sau").click().run()
    assert "Việc của An tháng 12" in html_tren_trang(at) and any("Tháng 12/2026" in s.value for s in at.subheader)
    at.button(key="lich_sau").click().run()
    assert "Việc quý sau" in html_tren_trang(at) and any("Tháng 1/2027" in s.value for s in at.subheader)
    at.button(key="lich_hom_nay").click().run()
    assert any("Tháng 11/2026" in s.value for s in at.subheader)
    at.button(key="lich_truoc").click().run()
    assert any("Tháng 10/2026" in s.value for s in at.subheader) and not at.exception


def test_the_so_lieu_theo_quy_dang_chon(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    the = html_tren_trang(at)
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">2</div>' in the      # V-1, V-3 (quý 4)
    assert f'<div class="gv-nhan">Quá hạn</div><div class="gv-so">1</div>' in the
    at.selectbox(key="tq_quy").set_value("2027-Q1").run()
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">1</div>' in html_tren_trang(at)


def test_co_hai_bieu_do(app_env):
    app_env(tasks=viec_vi_du_spec(da_duyet=True))
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and len(at.get("vega_lite_chart")) >= 2


def test_bang_trong_khong_sap_va_van_co_lich(app_env):
    app_env()
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and 'class="gv-lich"' in html_tren_trang(at)


def test_nhan_vien_chi_thay_viec_cua_minh_tren_lich_va_the(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception
    trang = html_tren_trang(at)
    assert "Việc của An tháng 11" in trang and "Việc của Bình quá hạn" not in trang
    assert "Nguyễn An" not in trang                         # lịch của nhân viên không cần ghi tên người nhận
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">3</div>' in trang
    assert f'<div class="gv-nhan">Quá hạn</div><div class="gv-so">0</div>' in trang


def test_ten_viec_co_the_html_khong_lot_ra_trang(app_env):
    app_env(tasks=[viec(Ten_Viec="<img src=x onerror=alert(1)>", Han_Chot="2026-11-20")])
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert "<img" not in html_tren_trang(at) and "&lt;img" in html_tren_trang(at)
